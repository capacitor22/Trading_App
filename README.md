# Trading App
Web Site to support stock trades and studies


OBS: Dados para crypto
    cryptodatadownload.com


# MODELO PARA O ARQUIVO config.py
## Criar arquivo config.py na raiz do projeto e colocar suas credenciais do ALPACA em API_KEY e SECRET_KEY

BASE_URL = "https://paper-api.alpaca.markets"
API_KEY = "xxxxxxxx"
SECRET_KEY = "xxxxxxxx"

{% if (dic_charts|length % 3) == 2 %}
    <div class="card border-0"></div>
{% elif (dic_charts|length % 3) == 1 %}
    <div class="card border-0"></div>
    <div class="card border-0"></div>
{% endif %}