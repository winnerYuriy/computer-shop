# shop/views_invoice.py

import os
from decimal import Decimal
from datetime import date
from io import BytesIO

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.db import transaction

# ReportLab
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping

# Моделі
from shop.models import LegalEntity, Product, Service, Invoice, InvoiceItem


# ====================== НАЛАШТУВАННЯ ШРИФТІВ ======================
def setup_fonts():
    """Правильна реєстрація кириличних шрифтів для ReportLab"""
    # Найкращі варіанти шрифтів для Fedora
    font_paths = [
        # 1. Liberation Sans (найкращий вибір для Fedora)
        ('LiberationSans', 
         '/usr/share/fonts/liberation/LiberationSans-Regular.ttf',
         '/usr/share/fonts/liberation/LiberationSans-Bold.ttf'),
        
        # 2. DejaVu Sans (дуже надійний)
        ('DejaVuSans', 
         '/usr/share/fonts/dejavu/DejaVuSans.ttf',
         '/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf'),
        
        # 3. Noto Sans (сучасний)
        ('NotoSans', 
         '/usr/share/fonts/google-noto/NotoSans-Regular.ttf',
         '/usr/share/fonts/google-noto/NotoSans-Bold.ttf'),
    ]

    for font_name, regular_path, bold_path in font_paths:
        try:
            # Реєструємо звичайний шрифт
            pdfmetrics.registerFont(TTFont(font_name, regular_path))
            # Реєструємо жирний шрифт
            pdfmetrics.registerFont(TTFont(f'{font_name}-Bold', bold_path))
            
            # Додаємо мапінг для кирилиці
            addMapping(font_name, 0, 0, font_name)
            addMapping(font_name, 0, 1, f'{font_name}-Bold')
            
            print(f"✅ Успішно зареєстровано шрифт: {font_name}")
            return font_name, f'{font_name}-Bold'
            
        except FileNotFoundError:
            continue
        except Exception as e:
            print(f"⚠️ Помилка при реєстрації {font_name}: {e}")
            continue

    # Якщо жоден шрифт не знайдено
    print("⚠️ Не вдалося знайти кириличні шрифти. Використовуємо Helvetica (без кирилиці!)")
    print("   Встановіть шрифти командою:")
    print("   sudo dnf install liberation-fonts dejavu-sans-fonts")
    return 'Helvetica', 'Helvetica-Bold'


# Виконуємо реєстрацію при імпорті модуля
DEFAULT_FONT, DEFAULT_FONT_BOLD = setup_fonts()


# ====================== ДОПОМІЖНІ ФУНКЦІЇ ======================

def get_next_invoice_number():
    """Генерує наступний номер рахунку у форматі РФ-2026-000001"""
    last_invoice = Invoice.objects.order_by('-invoice_number').first()
    if last_invoice and last_invoice.invoice_number:
        try:
            last_num = int(last_invoice.invoice_number.split('-')[-1])
            next_num = str(last_num + 1).zfill(6)
            return f"РФ-{date.today().strftime('%Y')}-{next_num}"
        except:
            pass
    return f"РФ-{date.today().strftime('%Y')}-000001"


# ====================== В'ЮХИ ======================

@staff_member_required
def invoice_form(request):
    """Форма створення рахунку"""
    legal_entities = LegalEntity.objects.filter(is_active=True)

    context = {
        'legal_entities': legal_entities,
        'invoice_number': get_next_invoice_number(),
        'invoice_date': date.today().strftime('%d.%m.%Y'),
    }
    return render(request, 'admin/invoice_form.html', context)


@staff_member_required
def search_products_api(request):
    """AJAX пошук товарів і послуг"""
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse([], safe=False)

    products = Product.objects.filter(title__icontains=query, available=True)[:12]
    services = Service.objects.filter(name__icontains=query, is_active=True)[:12]

    results = []

    for p in products:
        results.append({
            'id': p.id,
            'name': p.title,
            'price': str(p.price),
            'type': 'product',
            'type_label': 'Товар',
            'article': p.article or '',
        })

    for s in services:
        results.append({
            'id': s.id,
            'name': s.name,
            'price': str(s.price),
            'type': 'service',
            'type_label': s.get_service_type_display(),
        })

    return JsonResponse(results, safe=False)


@staff_member_required
def get_product_price(request):
    """Отримання ціни товару або послуги"""
    item_id = request.GET.get('id')
    item_type = request.GET.get('type', 'product')

    if item_type == 'product':
        obj = get_object_or_404(Product, id=item_id, available=True)
        return JsonResponse({
            'price': str(obj.price),
            'name': obj.title,
            'unit': 'шт'
        })

    elif item_type == 'service':
        obj = get_object_or_404(Service, id=item_id, is_active=True)
        return JsonResponse({
            'price': str(obj.price),
            'name': obj.name,
            'unit': obj.unit or 'шт'
        })

    return JsonResponse({'error': 'Не знайдено'}, status=404)


@staff_member_required
@transaction.atomic
def create_invoice(request):
    """Створення рахунку"""
    if request.method != 'POST':
        return redirect('invoice_form')

    legal_entity_id = request.POST.get('legal_entity')
    if not legal_entity_id:
        messages.error(request, 'Оберіть юридичну особу')
        return redirect('invoice_form')

    legal_entity = get_object_or_404(LegalEntity, id=legal_entity_id)

    # Збираємо дані з форми
    item_names = request.POST.getlist('item_name[]')
    item_quantities = request.POST.getlist('item_quantity[]')
    item_prices = request.POST.getlist('item_price[]')
    item_types = request.POST.getlist('item_type[]')
    item_ids = request.POST.getlist('item_id[]')

    items = []
    subtotal = Decimal('0')

    for i in range(len(item_names)):
        if not item_names[i] or not item_quantities[i] or not item_prices[i]:
            continue
        try:
            quantity = Decimal(item_quantities[i].replace(',', '.'))
            price = Decimal(item_prices[i].replace(',', '.'))
            total = quantity * price
            subtotal += total

            product = None
            service = None
            if item_types[i] == 'product' and item_ids[i]:
                product = Product.objects.filter(id=item_ids[i]).first()
            elif item_types[i] == 'service' and item_ids[i]:
                service = Service.objects.filter(id=item_ids[i]).first()

            items.append({
                'name': item_names[i],
                'quantity': quantity,
                'price': price,
                'total': total,
                'product': product,
                'service': service,
            })
        except Exception:
            continue

    if not items:
        messages.error(request, 'Додайте хоча б одну позицію')
        return redirect('invoice_form')

    vat_amount = 0 #subtotal * Decimal('0.2') ### БЕЗ ПДВ - ДЛЯ ПДВ прибрати одинарну #
    total_amount = subtotal + vat_amount

    # Створення рахунку
    invoice = Invoice.objects.create(
        legal_entity=legal_entity,
        subtotal=subtotal,
        vat_amount=vat_amount,
        total_amount=total_amount,
        created_by=request.user.username,
    )

    # Додавання позицій
    for item in items:
        InvoiceItem.objects.create(
            invoice=invoice,
            name=item['name'],
            quantity=item['quantity'],
            price=item['price'],
            total=item['total'],
        )

    messages.success(request, f'Рахунок №{invoice.invoice_number} успішно створено')
    return redirect('print_invoice', invoice_id=invoice.id)


@staff_member_required
def print_invoice(request, invoice_id):
    """Генерація PDF рахунку (оптимізована)"""
    invoice = get_object_or_404(Invoice, id=invoice_id)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=15*mm,
        bottomMargin=15*mm,
        leftMargin=15*mm,
        rightMargin=15*mm
    )

    styles = getSampleStyleSheet()
    normal_style = ParagraphStyle('Normal', parent=styles['Normal'],
                                  fontName=DEFAULT_FONT, fontSize=10, leading=12)
    bold_style = ParagraphStyle('Bold', parent=styles['Normal'],
                                fontName=DEFAULT_FONT_BOLD, fontSize=10, leading=12)
    title_style = ParagraphStyle('Title', parent=styles['Heading1'],
                                 fontName=DEFAULT_FONT_BOLD, fontSize=16,
                                 alignment=1, spaceAfter=12)

    elements = []

    # Заголовок
    elements.append(Paragraph("РАХУНОК-ФАКТУРА", title_style))
    elements.append(Spacer(1, 10))

    # Номер і дата
    header_data = [[f"№ {invoice.invoice_number}", f"від {invoice.invoice_date.strftime('%d.%m.%Y')}"]]
    header_table = Table(header_data, colWidths=[300, 200])
    header_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), DEFAULT_FONT_BOLD),
        ('FONTSIZE', (0, 0), (-1, -1), 13),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 15))

    # Реквізити
    rekv_data = [
        ["ПРОДАВЕЦЬ:", "ПОКУПЕЦЬ:"],
        [invoice.seller or "ТОВ 'Назва Фірми'", invoice.legal_entity.name],
        [f"Код ЄДРПОУ: {getattr(invoice, 'seller_code', '-')}", 
         f"Код ЄДРПОУ: {invoice.legal_entity.code_edrpou or '-'}"]
    ]

    rekv_table = Table(rekv_data, colWidths=[240, 240])
    rekv_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), DEFAULT_FONT_BOLD),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(rekv_table)
    elements.append(Spacer(1, 18))

    # Таблиця позицій
    table_data = [['№', 'Найменування', 'Кількість', 'Ціна', 'Сума']]

    for idx, item in enumerate(invoice.items.all(), 1):
        table_data.append([
            str(idx),
            Paragraph(item.name, normal_style),
            f"{item.quantity:.2f}",
            f"{item.price:.2f}",
            f"{item.total:.2f}"
        ])

    # Підсумки
    table_data.extend([
        ['', '', '', 'Разом без ПДВ:', f"{invoice.subtotal:.2f}"],
        ['', '', '', 'БЕЗ ПДВ:', f"{invoice.vat_amount:.2f}"],
        ['', '', '', 'ДО СПЛАТИ:', f"{invoice.total_amount:.2f}"],
    ])

    table = Table(table_data, colWidths=[30, 280, 50, 65, 70])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), DEFAULT_FONT_BOLD),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -4), 0.5, colors.grey),
        ('BOX', (0, -3), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, -3), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -3), (-1, -1), DEFAULT_FONT_BOLD),
        ('ALIGN', (2, 1), (4, -1), 'RIGHT'),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 25))

    # Банківські реквізити
    elements.append(Paragraph("<b>Банківські реквізити:</b>", bold_style))
    elements.append(Paragraph(f"Банк: {invoice.legal_entity.bank_name or '—'}", normal_style))
    elements.append(Paragraph(f"Р/р: {invoice.legal_entity.bank_account or '—'}", normal_style))
    elements.append(Paragraph(f"МФО: {invoice.legal_entity.bank_mfo or '—'}", normal_style))

    elements.append(Spacer(1, 30))
    elements.append(Paragraph("Виписав ___________________", normal_style))

    doc.build(elements)

    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Рахунок_{invoice.invoice_number}.pdf"'
    return response


@staff_member_required
def invoice_list(request):
    """Список усіх рахунків"""
    invoices = Invoice.objects.select_related('legal_entity').order_by('-invoice_date', '-invoice_number')

    # Фільтри
    if q := request.GET.get('invoice_number'):
        invoices = invoices.filter(invoice_number__icontains=q)
    if le_id := request.GET.get('legal_entity'):
        invoices = invoices.filter(legal_entity_id=le_id)

    paginator = Paginator(invoices, 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'invoices': page_obj,
        'legal_entities': LegalEntity.objects.filter(is_active=True),
    }
    return render(request, 'admin/invoice_list.html', context)