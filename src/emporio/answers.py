"""Grounded product templates: model routing, deterministic commercial facts."""
import re
from emporio.data import normalize


def render_online_return(result, question):
    """Use a narrow template only when the required rules are present in retrieval."""
    if not re.search(r'\b(return|returns|devolução|devolver|arrependimento)\b', question, re.I):
        return None
    passages=result.get('passages', [])
    for passage in passages:
        source=normalize(passage['text'])
        if ('7 (sete) dias corridos' in source and 'frete de devolucao e por conta da loja' in source):
            english=bool(re.search(r'\b(english|return|returns)\b',question,re.I))
            if english:
                return (f"According to the store manual (page {passage['page']}), online purchases have a seven-calendar-day return request period after actual receipt. "
                        "The store pays return shipping for withdrawal. The manual requires original packaging, no signs of use, and all accessories and manuals. "
                        "Please confirm the purchase was online and the actual receipt date if those details have not been provided. "
                        "Contact the store team to request the return; this assistant does not approve or register refunds.")
            return (f"Segundo o manual (página {passage['page']}), compras online permitem solicitar devolução por arrependimento em até sete dias corridos após o recebimento efetivo. "
                    "O frete de devolução é por conta da loja. O manual exige embalagem original, ausência de sinais de uso e todos os acessórios e manuais. "
                    "Confirme o canal da compra e a data de recebimento, caso ainda não tenha informado. Solicite a devolução à equipe; este assistente não aprova nem registra reembolsos.")
    return None


def render_products(result, question):
    english = bool(re.search(r'\b(english|show|what|price|please|available|guitars)\b', question, re.I))
    products = result['products']
    if not products:
        return ('No matching instruments were found in the supplied catalog snapshot. Please refine the model name or category.' if english else
                'Não encontrei instrumentos com esses filtros nos dados fornecidos. Podemos ajustar o nome do modelo ou a categoria?')
    lines = [('Catalog results (BRL):' if english else 'Resultados do catálogo (R$):')]
    for product in products:
        line = f"- {product['name']}: {product['price_brl']}"
        if product['promotion_active']:
            line += (f" (original {product['original_price_brl']}; {product['discount_percent']}% off)" if english else
                     f" (preço original {product['original_price_brl']}; desconto de {product['discount_percent']}%)")
        line += (f". Stock: {product['stock_quantity']}. Status: {product['status']}." if english else
                 f". Estoque: {product['stock_quantity']}. Status: {product['status']}.")
        lines.append(line)
    if any(p['payment'] == 'pix' and p['promotion_active'] for p in products):
        lines.append('The 5% PIX discount is not added to promotional prices (store manual, page 6).' if english else
                     'O desconto de 5% no PIX não é acumulado com preços promocionais (manual, página 6).')
    lines.append('Availability comes from the supplied CSV snapshot and does not reserve stock.' if english else
                 'Disponibilidade consultada nos CSVs fornecidos; esta consulta não reserva estoque.')
    return '\n'.join(lines)
