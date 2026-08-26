# Deploy no Streamlit Community Cloud

## Demonstração pública

1. Acesse [share.streamlit.io](https://share.streamlit.io/).
2. Selecione o repositório `fabioconceicao22/dashboard-wifi-uff-sbpc`.
3. Informe `app.py` como arquivo principal.
4. Faça o deploy.

A aplicação gera automaticamente uma base sintética em memória quando não encontra um histórico local. Nenhum arquivo de dados é necessário no repositório público.

## Ambiente operacional

Não envie `wifi_historico.pkl`, exportações do FortiAnalyzer, logs ou segredos para o GitHub. O Streamlit Community Cloud possui armazenamento efêmero e não é indicado como histórico operacional.

Para utilização institucional, recomenda-se:

- servidor interno com acesso controlado;
- `WIFI_HASH_SALT` configurado como segredo de ambiente;
- armazenamento persistente autorizado;
- integração com API ou exportação agendada do FortiAnalyzer;
- política de retenção e acesso alinhada à LGPD e às normas da UFF.

