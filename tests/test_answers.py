import unittest
from emporio.answers import render_products, render_online_return

class GroundedAnswersTests(unittest.TestCase):
    def test_promotional_pix_quote_is_rendered_without_stacking(self):
        quote={'name':'Demo Instrument','price_brl':'439.20','original_price_brl':'549.00',
               'discount_percent':'20','promotion_active':True,'stock_quantity':2,'status':'active','payment':'pix'}
        answer=render_products({'products':[quote]},'Please reply in English. What is its price?')
        self.assertIn('439.20',answer)
        self.assertIn('549.00',answer)
        self.assertIn('20% off',answer)
        self.assertIn('not added',answer)
        self.assertNotIn('417.24',answer)
    def test_missing_products_do_not_generate_prices(self):
        answer=render_products({'products':[]},'What is the price?')
        self.assertIn('No matching instruments',answer)
    def test_return_template_requires_source_rules(self):
        question='Please reply in English. Can I request a return?'
        self.assertIsNone(render_online_return({'passages':[]},question))
        result={'passages':[{'page':4,'text':'7 (sete) dias corridos. O frete de devolução é por conta da loja.'}]}
        answer=render_online_return(result,question)
        self.assertIn('seven-calendar-day',answer)
        self.assertIn('store pays',answer)
        self.assertIn('page 4',answer)
