from fastapi.templating import Jinja2Templates

# 大屏相关模板
bi_templates = {
    'index1': 'index1.html',
    'index2': 'index2.html',
}
bi_templates_env = Jinja2Templates(directory="templates")

# 指标管理相关模板
bi_data_templates = {
    'index': 'index.html',
    'contract_indicators': 'contract_indicators.html',
    'add_contract_indicator': 'add_contract_indicator.html',
    'kpi_indicators': 'kpi_indicators.html',
    'add_kpi_indicator': 'add_kpi_indicator.html',
    'edit': 'edit.html',
}
bi_data_templates_env = Jinja2Templates(directory="templates")
