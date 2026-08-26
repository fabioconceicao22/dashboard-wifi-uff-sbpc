from services.parser_fortianalyzer import importar_novos_arquivos

resumo = importar_novos_arquivos()

print()
print("IMPORTACAO CONCLUIDA")
print("--------------------")
print(f"Arquivos encontrados: {resumo['arquivos_encontrados']}")
print(f"Arquivos importados: {resumo['arquivos_importados']}")
print(f"Arquivos rejeitados: {resumo['arquivos_rejeitados']}")
print(f"Registros lidos: {resumo['registros_lidos']}")
print(f"Registros novos: {resumo['registros_novos']}")
print(f"Duplicados descartados: {resumo['duplicados_descartados']}")
print(f"Total no historico: {resumo['total_registros_historico']}")
print()

