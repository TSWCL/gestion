{
    'name': "TSW Gestión",
    'summary': "Módulo para la gestion de varias personalizaciones y optimizaciones en odoo",
    'description': """
        Este módulo añade un campo 'Vendedor' en el formulario de cuentas analíticas 
        (modelo account.analytic.account) para relacionarlo con el vendedor de ventas.
    """,
    'author': ['Adrian R. Hernandez Vidrio','Oscar F. Cárcamo Oyarzo'],
    'website': "www.totalsoftware.cl",
    'category': 'Custom',
    'version': '17.0.1.0.0',
    'depends': ['analytic', 'sale'],
    'data': [
        'views/analytic_account_view.xml',
    ],
    'installable': True,
    'application': True,
}