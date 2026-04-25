# shop/views_invoice.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.db import transaction
from decimal import Decimal
from datetime import date
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping
from io import BytesIO
from shop.models import LegalEntity, Product, Service, Invoice, InvoiceItem
from django.template.loader import render_to_string
from django.http import HttpResponse
from weasyprint import HTML

# ============================================================
# РЕЄСТРАЦІЯ КИРИЛИЧНИХ ШРИФТІВ ДЛЯ FEDORA
# ============================================================
try:
    pdfmetrics.registerFont(TTFont('LiberationSans', '/usr/share/fonts/liberation/LiberationSans-Regular.ttf'))
    pdfmetrics.registerFont(TTFont('LiberationSans-Bold', '/usr/share/fonts/liberation/LiberationSans-Bold.ttf'))
    DEFAULT_FONT = 'LiberationSans'
    DEFAULT_FONT_BOLD = 'LiberationSans-Bold'
    print("✅ Використовуємо шрифт Liberation Sans")
except:
    try:
        pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/dejavu/DejaVuSans.ttf'))
        pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', '/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf'))
        DEFAULT_FONT = 'DejaVuSans'
        DEFAULT_FONT_BOLD = 'DejaVuSans-Bold'
        print("✅ Використовуємо шрифт DejaVu Sans")
    except:
        try:
            pdfmetrics.registerFont(TTFont('FreeSans', '/usr/share/fonts/freefont/FreeSans.ttf'))
            pdfmetrics.registerFont(TTFont('FreeSans-Bold', '/usr/share/fonts/freefont/FreeSansBold.ttf'))
            DEFAULT_FONT = 'FreeSans'
            DEFAULT_FONT_BOLD = 'FreeSans-Bold'
            print("✅ Використовуємо шрифт Free Sans")
        except:
            try:
                pdfmetrics.registerFont(TTFont('NotoSans', '/usr/share/fonts/google-noto/NotoSans-Regular.ttf'))
                pdfmetrics.registerFont(TTFont('NotoSans-Bold', '/usr/share/fonts/google-noto/NotoSans-Bold.ttf'))
                DEFAULT_FONT = 'NotoSans'
                DEFAULT_FONT_BOLD = 'NotoSans-Bold'
                print("✅ Використовуємо шрифт Noto Sans")
            except:
                print("⚠️ Жоден кириличний шрифт не знайдено! Встановіть: sudo dnf install liberation-fonts")
                DEFAULT_FONT = 'Helvetica'
                DEFAULT_FONT_BOLD = 'Helvetica-Bold'

addMapping(DEFAULT_FONT, 0, 0, DEFAULT_FONT)
addMapping(DEFAULT_FONT, 0, 1, DEFAULT_FONT_BOLD)


@staff_member_required
def invoice_form(request):
    """Форма для виписки рахунку (стиль 1С)"""
    legal_entities = LegalEntity.objects.filter(is_active=True)
    
    last_invoice = Invoice.objects.order_by('-invoice_number').first()
    next_number = "000001"
    if last_invoice and last_invoice.invoice_number:
        try:
            last_num = int(last_invoice.invoice_number.split('-')[-1])
            next_number = str(last_num + 1).zfill(6)
        except:
            next_number = "000001"
    
    context = {
        'legal_entities': legal_entities,
        'invoice_number': f"РФ-{date.today().strftime('%Y')}-{next_number}",
        'invoice_date': date.today().strftime('%d.%m.%Y'),
    }
    return render(request, 'admin/invoice_form.html', context)


@staff_member_required
def search_products_api(request):
    """AJAX пошук товарів та послуг для рахунку"""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse([], safe=False)
    
    products = Product.objects.filter(
        title__icontains=query, 
        available=True
    )[:15]
    
    services = Service.objects.filter(
        name__icontains=query, 
        is_active=True
    )[:15]
    
    results = []
    
    for product in products:
        results.append({
            'id': product.id,
            'name': product.title,
            'price': str(product.price),
            'type': 'product',
            'type_label': '📦 Товар',
            'code': product.code or '',
            'article': product.article or '',
            'stock': product.quantity,
        })
    
    for service in services:
        results.append({
            'id': service.id,
            'name': service.name,
            'price': str(service.price),
            'type': 'service',
            'type_label': '🔧 Послуга',
            'code': '',
            'article': '',
            'stock': '',
        })
    
    return JsonResponse(results, safe=False)


@staff_member_required
@transaction.atomic
def create_invoice(request):
    """Створення рахунку з форми"""
    if request.method != 'POST':
        return redirect('invoice_form')
    
    try:
        legal_entity_id = request.POST.get('legal_entity')
        
        item_ids = request.POST.getlist('item_id[]')
        item_types = request.POST.getlist('item_type[]')
        item_names = request.POST.getlist('item_name[]')
        item_quantities = request.POST.getlist('item_quantity[]')
        item_prices = request.POST.getlist('item_price[]')
        
        if not legal_entity_id:
            messages.error(request, 'Оберіть юридичну особу')
            return redirect('invoice_form')
        
        legal_entity = get_object_or_404(LegalEntity, id=legal_entity_id)
        
        subtotal = Decimal('0')
        items = []
        
        for i in range(len(item_names)):
            if item_names[i] and item_quantities[i] and item_prices[i]:
                try:
                    quantity = Decimal(item_quantities[i].replace(',', '.'))
                    price = Decimal(item_prices[i].replace(',', '.'))
                    total = quantity * price
                    subtotal += total
                    
                    items.append({
                        'name': item_names[i],
                        'quantity': quantity,
                        'price': price,
                        'total': total,
                    })
                except:
                    continue
        
        if not items:
            messages.error(request, 'Додайте хоча б одну позицію')
            return redirect('invoice_form')
        
        vat_amount = subtotal * Decimal('0.2')
        total_amount = subtotal + vat_amount
        
        invoice = Invoice.objects.create(
            legal_entity=legal_entity,
            subtotal=subtotal,
            vat_amount=vat_amount,
            total_amount=total_amount,
            created_by=request.user.username,
        )
        
        for item in items:
            InvoiceItem.objects.create(
                invoice=invoice,
                name=item['name'],
                quantity=item['quantity'],
                price=item['price'],
                total=item['total'],
            )
        
        messages.success(request, f'✅ Рахунок №{invoice.invoice_number} створено')
        return redirect('print_invoice', invoice_id=invoice.id)
        
    except Exception as e:
        messages.error(request, f'❌ Помилка: {str(e)}')
        return redirect('invoice_form')


@staff_member_required
def print_invoice(request, invoice_id):
    """Друк рахунку в PDF (HTML шаблон)"""
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    # Генерація прописом (опціонально)
    total_words = num2words_uk(invoice.total_amount) if 'num2words_uk' in globals() else None
    
    context = {
        'invoice': invoice,
        'total_words': total_words,
    }
    
    html_string = render_to_string('invoice_template.html', context)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="рахунок_{invoice.invoice_number}.pdf"'
    
    try:
        from weasyprint import HTML
        HTML(string=html_string).write_pdf(response)
    except ImportError:
        # Якщо weasyprint не встановлено, повертаємо HTML
        return HttpResponse(html_string, content_type='text/html')
    
    return response


@staff_member_required
def invoice_list(request):
    """Список рахунків-фактур з фільтрами та пагінацією"""
    invoices = Invoice.objects.select_related('legal_entity').all()
    
    # Фільтр за номером рахунку
    invoice_number = request.GET.get('invoice_number')
    if invoice_number:
        invoices = invoices.filter(invoice_number__icontains=invoice_number)
    
    # Фільтр за юридичною особою
    legal_entity_id = request.GET.get('legal_entity')
    if legal_entity_id and legal_entity_id.isdigit():
        invoices = invoices.filter(legal_entity_id=int(legal_entity_id))
    
    # Фільтр за статусом оплати
    payment_status = request.GET.get('payment_status')
    if payment_status:
        invoices = invoices.filter(payment_status=payment_status)
    
    # Фільтр за датою від
    date_from = request.GET.get('date_from')
    if date_from:
        invoices = invoices.filter(invoice_date__gte=date_from)
    
    # Фільтр за датою до
    date_to = request.GET.get('date_to')
    if date_to:
        invoices = invoices.filter(invoice_date__lte=date_to)
    
    # Сортування за замовчуванням
    invoices = invoices.order_by('-invoice_date', '-invoice_number')
    
    # Пагінація
    paginator = Paginator(invoices, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'invoices': page_obj,
        'legal_entities': LegalEntity.objects.filter(is_active=True),
    }
    return render(request, 'admin/invoice_list.html', context)


def num2words_uk(amount):
    """Перетворює число в текст прописом українською мовою"""
    units = ["", "одна", "дві", "три", "чотири", "п'ять", "шість", "сім", "вісім", "дев'ять"]
    teens = ["десять", "одинадцять", "дванадцять", "тринадцять", "чотирнадцять", 
             "п'ятнадцять", "шістнадцять", "сімнадцять", "вісімнадцять", "дев'ятнадцять"]
    tens = ["", "десять", "двадцять", "тридцять", "сорок", "п'ятдесят", 
            "шістдесят", "сімдесят", "вісімдесят", "дев'яносто"]
    hundreds = ["", "сто", "двісті", "триста", "чотириста", "п'ятсот", 
                "шістсот", "сімсот", "вісімсот", "дев'ятсот"]

    def number_to_words(num):
        if num == 0:
            return "нуль"
        words = []
        
        # Сотні
        h = num // 100
        if h > 0:
            if h < len(hundreds):
                words.append(hundreds[h])
            num %= 100
        
        # Десятки та одиниці
        if 10 <= num <= 19:
            words.append(teens[num - 10])
        else:
            t = num // 10
            if t > 0 and t < len(tens):
                words.append(tens[t])
            u = num % 10
            if u > 0:
                if u < len(units):
                    words.append(units[u])
        
        return " ".join(words) if words else "нуль"

    # Округлюємо до 2 знаків
    amount_rounded = round(float(amount), 2)
    amount_int = int(amount_rounded)
    kopiyky = int(round((amount_rounded - amount_int) * 100))
    
    # Визначаємо правильне закінчення для гривень
    last_digit = amount_int % 10
    last_two_digits = amount_int % 100
    
    if 11 <= last_two_digits <= 14:
        currency_word = "гривень"
    elif last_digit == 1:
        currency_word = "гривня"
    elif 2 <= last_digit <= 4:
        currency_word = "гривні"
    else:
        currency_word = "гривень"
    
    # Визначаємо правильне закінчення для копійок
    kop_last_digit = kopiyky % 10
    kop_last_two = kopiyky % 100
    
    if 11 <= kop_last_two <= 14:
        kop_word = "копійок"
    elif kop_last_digit == 1:
        kop_word = "копійка"
    elif 2 <= kop_last_digit <= 4:
        kop_word = "копійки"
    else:
        kop_word = "копійок"
    
    result = number_to_words(amount_int)
    
    return f"{result} {currency_word} {kopiyky:02d} {kop_word}"