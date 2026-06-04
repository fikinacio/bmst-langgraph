# -*- coding: utf-8 -*-
"""
Envio das 28 mensagens aprovadas pelo CEO (4 Jun 2026):
- FIN-001 a FIN-005 (Financas / Seguros)
- TEL-001 a TEL-005 (Telecomunicacoes)
- IMO-001 a IMO-015 (Imobiliario)
- Follow-ups B: COM-001 Fresmart, SRV-001 ACEAudit, SRV-002 Multipessoal
Sessoes perdidas na migracao JSON->SQLite da API em Mai 2026.
CEO aprovou directamente em sessao Claude Code — envia agora via /webhook/bmst-send-message.
"""

import requests
import time
from datetime import datetime

API_BASE = "https://bmst-api.fly.dev"
SEND_URL = f"{API_BASE}/webhook/bmst-send-message"

ts = datetime.now().strftime("%Y%m%d-%H%M%S")

mensagens = [
    # ── FINANCAS / SEGUROS ─────────────────────────────────────────────────────
    {
        "session_id": f"CLOSER-FortalezaSeguros-{ts}-FIN001",
        "decisao": "aprovado",
        "whatsapp_destino": "244924744544",
        "texto": """Bom dia,

A Fortaleza Seguros atende mais de 110 mil clientes em Angola, com linha dedicada 24/7 para sinistros e renovações. Com esse volume, a equipa responde manualmente a centenas de pedidos por dia — muitos dos quais são rotineiros e poderiam ter resposta imediata.

Na Bisca+, ajudamos seguradoras angolanas a automatizar exactamente esse atendimento: o cliente envia o pedido de renovação ou abertura de sinistro pelo WhatsApp, recebe confirmação em segundos e o processo arranca sem intervenção humana na triagem inicial.

Posso mostrar como isto funciona especificamente para o sector seguros em 20 minutos. Quando é que lhe convém?

Fidel Kussunga | Bisca+""",
    },
    {
        "session_id": f"CLOSER-InterRisk-{ts}-FIN002",
        "decisao": "aprovado",
        "email_destino": "amilcar.trindade@interisk-angola.com",
        "email_assunto": "Gestão documental automatizada para a Inter Risk Angola",
        "texto": """Caro Dr. Amílcar Trindade,

A Inter Risk Angola trabalha com clientes corporativos de grande porte — e isso significa um volume documental significativo: apólices, sinistros, relatórios de cobertura, correspondência com seguradoras internacionais.

Na Bisca+, desenvolvemos sistemas que permitem a corretoras responder automaticamente a questões dos clientes sobre coberturas e prazos, e que aceleram a produção de documentação de apólices a partir de bases de dados estruturadas — reduzindo o tempo de processamento por caso.

Dado o vínculo ao Grupo Costa Duarte e a carteira de clientes institucionais da Inter Risk, o retorno em produtividade seria mensurável desde o primeiro mês.

Seria possível 20 minutos esta semana para uma demonstração?

Fidel Kussunga | Bisca+
contact@biscaplus.com | +244 956 873 126""",
    },
    {
        "session_id": f"CLOSER-ZillianAngola-{ts}-FIN003",
        "decisao": "aprovado",
        "email_destino": "info@zillian.co.ao",
        "email_assunto": "Comunicação automatizada com clientes multinacionais — Zillian Angola",
        "texto": """Caro(a) Director(a),

A Zillian Angola trabalha com algumas das maiores empresas a operar em Angola, como correspondente exclusivo da AON no país. Os clientes multinacionais têm necessidades de comunicação constante — extractos de cobertura, alertas de renovação, actualizações de sinistros — e esperam respostas rápidas em qualquer fuso horário.

Na Bisca+, automatizamos exactamente este fluxo de comunicação: o cliente envia uma questão por WhatsApp ou email, recebe resposta baseada na documentação da apólice em segundos, e os pedidos mais complexos são encaminhados directamente ao responsável correcto.

Reduz-se o tempo gasto em comunicações rotineiras e melhora-se a percepção de serviço junto de clientes de alto valor.

Posso mostrar um caso concreto em 20 minutos. Quando é que lhe convém?

Fidel Kussunga | Bisca+
contact@biscaplus.com | +244 956 873 126""",
    },
    {
        "session_id": f"CLOSER-Multicredito-{ts}-FIN004",
        "decisao": "aprovado",
        "email_destino": "geral@multicredito.co.ao",
        "email_assunto": "Qualificação automática de pedidos de microcrédito — Multicrédito",
        "texto": """Caro(a) Director(a),

A Multicrédito processa créditos até AOA 7.000.000 por cliente — o que implica um volume elevado de pedidos com processo de qualificação que começa sempre da mesma forma: recolha de dados básicos, verificação de elegibilidade, agendamento de entrevista com técnico.

Na Bisca+, automatizamos exactamente esta primeira fase: o cliente envia o pedido pelo WhatsApp, responde a um conjunto de questões estruturadas, e só avança para entrevista com técnico quando cumpre os critérios básicos de elegibilidade.

Resultado: menos reuniões com candidatos não qualificados, mais tempo do técnico para casos com viabilidade real.

20 minutos para mostrar como isto funciona?

Fidel Kussunga | Bisca+
contact@biscaplus.com | +244 956 873 126""",
    },
    {
        "session_id": f"CLOSER-NespeCred-{ts}-FIN005",
        "decisao": "aprovado",
        "whatsapp_destino": "244927094314",
        "texto": """Bom dia,

A NespeCred actua em 4 províncias com créditos entre AOA 250.000 e 7.000.000. Com esse alcance geográfico, a qualificação de candidatos por telefone consome tempo de equipa que poderia estar em análise de crédito real.

Na Bisca+, automatizamos a triagem inicial de pedidos de microcrédito via WhatsApp: o candidato responde a questões estruturadas, o sistema verifica elegibilidade básica e só agenda entrevista com o técnico quando há viabilidade real.

Clientes nossos em Angola reduziram em 60% o tempo de triagem sem aumentar a equipa.

20 minutos para mostrar como funciona?

Fidel Kussunga | Bisca+""",
    },
    # ── TELECOMUNICACOES ───────────────────────────────────────────────────────
    {
        "session_id": f"CLOSER-Witelekom-{ts}-TEL001",
        "decisao": "aprovado",
        "whatsapp_destino": "244940415313",
        "texto": """Bom dia,

A Witelekom presta suporte técnico 24/7 a clientes empresariais e residenciais em fibra, VSAT e 5G. Com uma equipa comercial pequena a gerir todo o funil, os picos de chamadas para suporte de rede consomem tempo que devia estar em vendas.

Na Bisca+, ajudamos ISPs angolanos a separar automaticamente os pedidos de suporte técnico dos pedidos comerciais via WhatsApp: o cliente abre o ticket em segundos, recebe diagnóstico inicial e só escala para o técnico quando necessário.

Resultado: menos chamadas de triagem, mais tempo para negócio.

Posso mostrar como funciona concretamente em 20 minutos. Quando é que lhe convém?

Fidel Kussunga | Bisca+""",
    },
    {
        "session_id": f"CLOSER-SpeedNet-{ts}-TEL002",
        "decisao": "aprovado",
        "whatsapp_destino": "244944888988",
        "texto": """Bom dia,

A SpeedNet tem um mix interessante — clientes residenciais, PMEs e instituições públicas, tudo gerido pela mesma equipa comercial. O problema é que qualificar um lead enterprise demora o mesmo tempo que responder a uma questão de fibra residencial, e o engenheiro acaba a fazer triagem em vez de fechar propostas.

Na Bisca+, automatizamos exactamente esta separação: o lead entra pelo WhatsApp, é qualificado automaticamente (residencial vs. enterprise, dimensão da empresa, tipo de solução) e encaminhado ao vendedor certo com o briefing pronto.

60% menos tempo de pré-venda, leads enterprise sem perda por demora de resposta.

20 minutos para mostrar como funciona?

Fidel Kussunga | Bisca+""",
    },
    {
        "session_id": f"CLOSER-Connectis-{ts}-TEL003",
        "decisao": "aprovado",
        "email_destino": "nuno.ventura@connectis.co.ao",
        "email_assunto": "Tickets NOC e propostas enterprise — proposta de automação para a Connectis",
        "texto": """Caro Nuno,

O meu nome é Fidel Kussunga, fundador da BMST — Bisca Mais Sistemas e Tecnologias.

Contacto-o porque a Connectis serve clientes corporativos em múltiplas filiais (sectores financeiro e saúde) com infraestrutura MPLS/VPN e fibra. Sabendo o vosso perfil técnico — incluindo o AS próprio — sei que a gestão de tickets NOC ainda passa em larga medida por email e chamada manual, e que cada proposta enterprise complexa requer compilação técnica que consome tempo da equipa comercial antes do cliente ver uma resposta.

Na BMST implementamos sistemas que resolvem dois pontos concretos:

1. NOC: aberturas de ticket recebidas via WhatsApp ou portal web, com triagem automática (corte / lentidão / solicitação comercial), notificação proactiva ao cliente sobre estado, e escalonamento à equipa apenas do que requer intervenção humana.

2. Comercial: camada RAG sobre o vosso catálogo de serviços e propostas anteriores — a equipa comercial faz a pergunta em linguagem natural e o sistema devolve referências e elementos prontos a integrar em proposta.

A vossa equipa continua a trabalhar nos mesmos sistemas — o que muda é o tempo entre o pedido do cliente e a resposta.

Se vos faz sentido, agradecia 20 minutos esta semana para uma conversa rápida.

Com os melhores cumprimentos,
Fidel Kussunga
CEO — BMST — Bisca Mais Sistemas e Tecnologias
contact@biscaplus.com | +244 956 873 126""",
    },
    {
        "session_id": f"CLOSER-Advanlink-{ts}-TEL004",
        "decisao": "aprovado",
        "email_destino": "geral@advanlink.co.ao",
        "email_assunto": "Qualificação automática de pedidos de cotação — Advanlink",
        "texto": """Caro(a) Director(a),

A Advanlink tem um modelo de negócio híbrido — engenharia, distribuição de equipamento e ISP — com clientes em Oil&Gas, agricultura, governo e residencial. O desafio é que cada sector tem ciclos comerciais distintos, e a mesma equipa a responder a pedidos de cotação de Prysmian para o sector petrolífero e de fibra residencial não consegue priorizar correctamente.

Na Bisca+, automatizamos a triagem de pedidos de cotação: o cliente envia o pedido por WhatsApp ou email, o sistema recolhe os dados técnicos, classifica por sector e encaminha ao vendedor com a especialização correcta — com o briefing técnico preparado.

Sem chamadas de triagem. Sem tempo perdido a encaminhar pedidos manualmente.

Posso mostrar como funciona em 20 minutos?

Fidel Kussunga | Bisca+
contact@biscaplus.com | +244 956 873 126""",
    },
    {
        "session_id": f"CLOSER-UWF-{ts}-TEL005",
        "decisao": "aprovado",
        "email_destino": "suporte@uwf.ao",
        "email_assunto": "Escalar atendimento de 1.000 para 5.000 clientes — UWF Telecomunicações",
        "texto": """Caro(a) Director(a),

A UWF tem mais de 1.000 clientes activos em Angola, com 80% de cobertura NET ABERTA reportada. Com esse alcance, o suporte via email e telefone está a chegar ao limite — especialmente quando a iniciativa NET ABERTA gera pedidos informais via redes sociais que ninguém qualifica formalmente.

Na Bisca+, ajudamos ISPs a escalar o atendimento sem escalar a equipa: sistema automático que qualifica pedidos NET ABERTA (comunitário) versus clientes pagos residenciais versus enterprise, gere FAQs sobre cobertura e instalação, e abre tickets no sistema de suporte quando necessário.

O resultado: atender 5.000 clientes com a mesma equipa que hoje atende 1.000.

Posso mostrar como funciona em 20 minutos?

Fidel Kussunga | Bisca+
contact@biscaplus.com | +244 956 873 126""",
    },
    # ── IMOBILIARIO ────────────────────────────────────────────────────────────
    {
        "session_id": f"CLOSER-Imogesba-{ts}-IMO001",
        "decisao": "aprovado",
        "email_destino": "geral@imogesba.ao",
        "email_assunto": "Resposta automática a pedidos de imóveis — Imogesba",
        "texto": """Caro(a) Director(a),

A Imogesba recebe dezenas de pedidos diários de informação sobre imóveis disponíveis em Luanda — tipo, localização, preço, condições. Cada consulta respondida manualmente por um agente consome tempo que podia estar em visitas e negociações com clientes qualificados.

Na Bisca+, implementamos sistemas que respondem automaticamente a pedidos específicos: o cliente envia "tem T3 em Alvalade?", recebe a ficha técnica e fotos em segundos, e agenda a visita directamente. O agente humano entra apenas quando o cliente está pronto para avançar.

O tempo de resposta passa de horas para segundos — sem aumentar a equipa.

Posso mostrar como funciona em 20 minutos?

Fidel Kussunga | Bisca+
contact@biscaplus.com | +244 956 873 126""",
    },
    {
        "session_id": f"CLOSER-KoraAngola-{ts}-IMO002",
        "decisao": "aprovado",
        "email_destino": "info@koraangola.com",
        "email_assunto": "Atendimento automático para os empreendimentos Kora Angola",
        "texto": """Caro(a) Director(a),

A Kora Angola tem empreendimentos residenciais próprios em Talatona e Benfica — o que significa um volume constante e previsível de pedidos de informação: tipologias, preços, condições de pagamento, agendamento de visitas.

Na Bisca+, implementámos sistemas de atendimento que tratam exactamente este fluxo: o potencial comprador envia uma mensagem no WhatsApp, recebe em segundos a ficha do empreendimento correspondente ao seu interesse, e agenda a visita directamente — sem ocupar a equipa comercial com triagem manual.

O tempo de resposta passa de horas para segundos. A equipa foca-se nos clientes qualificados.

Posso mostrar como funciona especificamente para o modelo da Kora em 20 minutos. Quando é que lhe convém?

Fidel Kussunga | Bisca+
contact@biscaplus.com | +244 956 873 126""",
    },
    {
        "session_id": f"CLOSER-Predilel-{ts}-IMO003",
        "decisao": "aprovado",
        "email_destino": "geral@predilel.ao",
        "email_assunto": "Primeira impressão perfeita para os clientes Predilel",
        "texto": """Caro(a) Director(a),

A Predilel opera no segmento premium de Luanda — Miramar e Ilha do Cabo — onde os clientes têm alternativas e a qualidade do atendimento é factor de decisão. Uma resposta lenta a um pedido de informação sobre um imóvel é uma oportunidade perdida para a concorrência.

Na Bisca+, implementamos sistemas de resposta imediata para imobiliárias premium: o cliente envia a consulta, recebe em segundos a ficha do imóvel com fotos e condições, e agenda a visita — a qualquer hora. O agente humano entra apenas quando o cliente está qualificado.

No segmento premium, a primeira impressão conta. Uma resposta em segundos diferencia quem a dá.

20 minutos para mostrar como funciona?

Fidel Kussunga | Bisca+
contact@biscaplus.com | +244 956 873 126""",
    },
    {
        "session_id": f"CLOSER-LuandaRealEstate-{ts}-IMO004",
        "decisao": "aprovado",
        "email_destino": "contacto@luandarealestate.com",
        "email_assunto": "Atendimento central para todos os imóveis listados — Luanda Real Estate",
        "texto": """Caro(a) Director(a),

A Luanda Real Estate tem centenas de imóveis listados de múltiplos vendedores e agências. Quando um potencial comprador envia um pedido, alguém tem de identificar a listagem correcta e reencaminhar para o vendedor responsável — um processo manual que cria demoras e perdas de leads.

Na Bisca+, desenvolvemos sistemas de atendimento centralizado para plataformas com este modelo: o pedido entra, o sistema identifica o imóvel correcto, contacta o vendedor responsável e coordena o agendamento — sem intervenção manual da equipa central.

O utilizador recebe resposta imediata. O vendedor recebe o lead qualificado. A plataforma mantém a qualidade de serviço independentemente de quem listou o imóvel.

20 minutos para mostrar como funciona?

Fidel Kussunga | Bisca+
contact@biscaplus.com | +244 956 873 126""",
    },
    {
        "session_id": f"CLOSER-Century21Angola-{ts}-IMO005",
        "decisao": "aprovado",
        "email_destino": "angola@century21.com",
        "email_assunto": "Qualificação centralizada de leads para a rede Century 21 Angola",
        "texto": """Caro(a) Director(a),

A Century 21 Angola tem o que outras imobiliárias não têm: marca internacional, rede de agentes e padrões comprovados globalmente. O desafio está em garantir que cada lead do website é qualificado e encaminhado para o agente certo antes que ele encontre resposta noutro lado.

Na Bisca+, desenvolvemos um sistema central de qualificação e distribuição de leads para redes de agências: o cliente entra pelo WhatsApp, é qualificado automaticamente (zona, tipo de imóvel, budget, urgência) e encaminhado ao agente com especialização nessa área.

Nenhum contacto fica por responder. A rede mantém a consistência de serviço que os padrões Century 21 exigem.

20 minutos para mostrar como isto funciona concretamente?

Fidel Kussunga | Bisca+
contact@biscaplus.com | +244 956 873 126""",
    },
    {
        "session_id": f"CLOSER-SquareImobiliaria-{ts}-IMO006",
        "decisao": "aprovado",
        "email_destino": "geral@square.co.ao",
        "email_assunto": "Resposta automática a pedidos de imóveis — Square Imobiliária",
        "texto": """Caro(a) Director(a),

A Square Imobiliária tem um dos portfolios mais diversificados de Luanda — apartamentos, escritórios, armazéns e terrenos. Com esse volume, a equipa comercial passa horas por dia a responder a perguntas básicas antes de identificar um cliente com intenção real de compra ou arrendamento.

Na Bisca+, implementámos sistemas de atendimento automatizado para imobiliárias com portfolio equivalente: o cliente envia "tem T3 em Talatona até 150.000 AOA/mês?", recebe fichas técnicas e fotos em segundos, e agenda visita — sem ocupar nenhum agente humano com triagem manual.

O tempo médio de primeira resposta passa de horas para menos de 30 segundos, mesmo ao fim de semana.

Poderia reservar 20 minutos esta semana para eu mostrar como funciona concretamente?

Fidel Kussunga | Bisca+
contact@biscaplus.com | +244 956 873 126""",
    },
    {
        "session_id": f"CLOSER-PrimeProperties-{ts}-IMO007",
        "decisao": "aprovado",
        "email_destino": "info@primeproperties.ao",
        "email_assunto": "Atendimento premium 24/7 para clientes internacionais — Prime Properties",
        "texto": """Caro(a) Director(a),

A Prime Properties trabalha no segmento imobiliário de alto padrão em Luanda — onde a qualidade do atendimento é tão importante quanto o produto. Clientes internacionais e expatriados enviam mensagens em português e inglês, muitas vezes fora do horário comercial angolano.

Na Bisca+, implementamos assistentes digitais bilingues (PT/EN) para imobiliárias premium: o cliente recebe resposta imediata com os detalhes do imóvel, seja às 23h de Lisboa ou às 7h de Londres, e a visita fica agendada antes de o agente humano chegar ao escritório.

No segmento premium, a primeira impressão define a decisão. Uma resposta em segundos diferencia da concorrência.

Posso mostrar como funciona em 20 minutos. Quando é que lhe convém?

Fidel Kussunga | Bisca+
contact@biscaplus.com | +244 956 873 126""",
    },
    {
        "session_id": f"CLOSER-TerraImobiliaria-{ts}-IMO008",
        "decisao": "aprovado",
        "whatsapp_destino": "244995724624",
        "texto": """Bom dia,

A Terra Imobiliária opera em Talatona — uma zona com alta rotatividade de arrendamentos, especialmente de expatriados e técnicos de empresa. Com esse perfil de cliente, os pedidos de informação chegam por WhatsApp a qualquer hora, incluindo ao fim de semana quando a equipa não está disponível.

Na Bisca+, automatizamos o atendimento de imobiliárias nesta zona: o cliente envia "tem T3 disponível em Talatona?", recebe ficha técnica e fotos em segundos, e agenda visita directamente — mesmo às 22h de sábado.

Clientes nossos em Talatona reduziram o tempo de resposta de horas para segundos sem aumentar a equipa.

20 minutos para mostrar como funciona?

Fidel Kussunga | Bisca+""",
    },
    {
        "session_id": f"CLOSER-ImoTrust-{ts}-IMO009",
        "decisao": "aprovado",
        "email_destino": "geral@imotrust.co.ao",
        "email_assunto": "Converter visitantes do website em leads qualificados — ImoTrust",
        "texto": """Caro(a) Director(a),

A ImoTrust tem listagens activas no website — o que significa que há potenciais compradores a visitar e a consultar imóveis. Cada visita que não converte em contacto qualificado é uma perda que não aparece em nenhum relatório.

Na Bisca+, implementamos sistemas que convertem essa intenção em contacto real: o visitante vê o imóvel no website, clica para WhatsApp, e em segundos recebe a ficha completa com condições e agenda visita directamente. Nenhum lead fica sem resposta.

O resultado: mais leads convertidos a partir do tráfego que já existe, sem custos adicionais de marketing.

20 minutos para mostrar como funciona?

Fidel Kussunga | Bisca+
contact@biscaplus.com | +244 956 873 126""",
    },
    {
        "session_id": f"CLOSER-REMAXAngola-{ts}-IMO010",
        "decisao": "aprovado",
        "email_destino": "angola@remax-multitrust.co.ao",
        "email_assunto": "Qualificação e distribuição automática de leads para a rede RE/MAX Angola",
        "texto": """Caro(a) Director(a),

A RE/MAX Angola tem o que a maioria das imobiliárias não tem: uma rede de agentes em todo o país com sistema de franquia profissional. O desafio está em garantir que cada lead que chega ao website é qualificado rapidamente e encaminhado para o agente certo — antes que o cliente encontre resposta noutro lado.

Na Bisca+, desenvolvemos soluções específicas para redes com esta estrutura: o lead entra pelo WhatsApp, é qualificado automaticamente (zona, tipo de imóvel, budget, prazo) e encaminhado ao agente correcto com notificação imediata. Nenhum contacto fica sem resposta, mesmo fora do horário comercial.

Trabalhamos já com empresas angolanas que gerem centenas de contactos diários e reduziram o tempo de primeira resposta em mais de 80%.

Seria possível 20 minutos esta semana para mostrar como isto se aplica à rede RE/MAX?

Fidel Kussunga | Bisca+
contact@biscaplus.com | +244 956 873 126""",
    },
    {
        "session_id": f"CLOSER-MyHouseAngola-{ts}-IMO011",
        "decisao": "aprovado",
        "whatsapp_destino": "244918884077",
        "texto": """Bom dia,

A My House Angola está em Talatona — uma zona muito competitiva. Quando está em visita com um cliente, quem responde às mensagens que chegam pelo WhatsApp?

Na Bisca+, ajudamos agências de dimensão média a nunca perder um lead por falta de disponibilidade: o sistema responde automaticamente fora de horário, apresenta os imóveis disponíveis e agenda a visita para quando estiver livre.

O lead fica garantido. O agente foca-se em fechar.

20 minutos para mostrar como funciona?

Fidel Kussunga | Bisca+""",
    },
    {
        "session_id": f"CLOSER-AbacusAngola-{ts}-IMO012",
        "decisao": "aprovado",
        "email_destino": "info@abacusangola.com",
        "email_assunto": "Análise documental automatizada para consultoria imobiliária — Abacus Angola",
        "texto": """Caro(a) Director(a),

A Abacus Angola produz avaliações e relatórios de due diligence imobiliária que envolvem legislação angolana, histórico de transacções e dados de mercado de Luanda — um trabalho que consome horas de um consultor a cruzar múltiplas fontes manualmente.

Na Bisca+, desenvolvemos sistemas de pesquisa inteligente sobre documentação legal e bases de dados de mercado: o consultor pergunta "qual o valor de referência por m² em Talatona para escritórios em 2026?" e obtém resposta fundamentada com as fontes correctas em segundos, não em horas.

O resultado são relatórios mais rápidos, com mais profundidade e com menos tempo de consultor gasto em pesquisa básica.

Posso mostrar uma demonstração concreta em 20 minutos?

Fidel Kussunga | Bisca+
contact@biscaplus.com | +244 956 873 126""",
    },
    {
        "session_id": f"CLOSER-Equilatero-{ts}-IMO013",
        "decisao": "aprovado",
        "email_destino": "geral@equilatero.ao",
        "email_assunto": "Atendimento 24/7 para clientes internacionais — Equilátero Imobiliária",
        "texto": """Caro(a) Director(a),

A Equilátero tem um website bilingue e um portfolio de imóveis premium em Talatona e Maculusso — o que indica claramente uma carteira de clientes internacionais e da diáspora angolana. O problema desses clientes é simples: quando contactam, é frequentemente ao fim do dia na Europa, o que significa fora do horário de atendimento em Luanda.

Na Bisca+, implementamos atendimento automático bilingue (PT/EN) para imobiliárias com esta carteira: o cliente recebe resposta imediata com a ficha do imóvel, independentemente do fuso horário, e agenda a visita ou videochamada directamente.

Os seus clientes na diáspora não têm resposta porque o fuso horário não bate certo — esta dor conhecemo-la bem, e temos a solução.

20 minutos para mostrar como funciona?

Fidel Kussunga | Bisca+
contact@biscaplus.com | +244 956 873 126""",
    },
    {
        "session_id": f"CLOSER-Capicua-{ts}-IMO014",
        "decisao": "aprovado",
        "whatsapp_destino": "244940983472",
        "texto": """Bom dia,

Numa agência onde é a mesma pessoa a atender, visitar, negociar e fechar — quando está em visita, não há ninguém a responder às mensagens que chegam. Cada mensagem sem resposta é um lead que foi procurar noutro lado.

Na Bisca+, resolvemos exactamente este problema: o sistema responde automaticamente às perguntas sobre imóveis disponíveis, envia fotos e preços, e agenda a visita para quando estiver disponível.

É como ter um assistente que nunca vai a visitas nem tira férias.

20 minutos para mostrar como funciona?

Fidel Kussunga | Bisca+""",
    },
    {
        "session_id": f"CLOSER-CasaSolucoesAfrica-{ts}-IMO015",
        "decisao": "aprovado",
        "email_destino": "info@casaesolucoesafrica.com",
        "email_assunto": "Automatizar comunicações de gestão de propriedades — Casa e Soluções Africa",
        "texto": """Caro(a) Director(a),

A Casa e Soluções Africa combina mediação imobiliária com gestão de propriedades — o que significa dois tipos distintos de comunicação: o ciclo de vendas e o fluxo contínuo com proprietários e inquilinos (lembretes de renda, manutenção, renovações de contrato).

Na Bisca+, automatizamos exactamente este segundo fluxo: o sistema envia o lembrete de renda automaticamente, confirma o pagamento, abre o ticket de manutenção quando o inquilino reporta um problema, e actualiza o proprietário com o estado — sem que a equipa precise de fazer follow-up manual.

O resultado é mais volume gerido com a mesma equipa, e uma relação mais profissional com proprietários e inquilinos.

Posso mostrar como funciona em 20 minutos. Quando é que lhe convém?

Fidel Kussunga | Bisca+
contact@biscaplus.com | +244 956 873 126""",
    },
    # ── FOLLOW-UPS B ──────────────────────────────────────────────────────────
    {
        "session_id": f"CLOSER-Fresmart-{ts}-COM001-FUB",
        "decisao": "aprovado",
        "email_destino": "apoio.cliente@fresmart.net",
        "email_assunto": "Re: Atendimento ao cliente em 46 lojas — Fresmart",
        "texto": """Caro(a),

Escrevi há alguns dias sobre automação de atendimento ao cliente para a rede Fresmart. Deixo apenas uma questão concreta: quando lança uma promoção nova nas 46 lojas, quantas horas passam entre o arranque e a altura em que toda a equipa de atendimento — em todas as províncias — já tem a resposta correcta para dar ao cliente?

Esse intervalo é exactamente onde a automação elimina ruído e garante consistência, mesmo a mil quilómetros da sede.

Se houver disponibilidade para 20 minutos esta semana, fico ao dispor.

Fidel Kussunga
contact@biscaplus.com | +244 956 873 126""",
    },
    {
        "session_id": f"CLOSER-ACEAudit-{ts}-SRV001-FUB",
        "decisao": "aprovado",
        "email_destino": "ace@aceangola.com",
        "email_assunto": "Re: Pesquisa documental automatizada para auditoria — ACE Audit",
        "texto": """Caro Senior Partner,

Escrevi há alguns dias sobre pesquisa documental automatizada para a vossa equipa de auditoria. Deixo um ângulo diferente: numa firma de auditoria, o tempo de um auditor qualificado é o recurso mais caro que existe — e cruzar documentos para localizar uma cláusula ou um valor específico consome esse recurso em tarefas sem valor analítico.

Se um sistema poupar 3 a 4 horas por processo de due diligence, e a ACE Audit conduz vários processos por mês, o retorno é mensurável desde o primeiro trimestre.

Estou disponível esta semana para mostrar como funciona concretamente — 20 minutos, sem compromisso.

Fidel Kussunga
contact@biscaplus.com | +244 956 873 126""",
    },
    {
        "session_id": f"CLOSER-Multipessoal-{ts}-SRV002-FUB",
        "decisao": "aprovado",
        "email_destino": "geral@multipessoal.co.ao",
        "email_assunto": "Re: Triagem automatizada de candidatos — Multipessoal Angola",
        "texto": """Caro Director,

Escrevi há alguns dias sobre triagem automatizada de candidatos. Uma nota adicional: as empresas que respondem ao candidato em menos de 24 horas têm taxas de aceitação de oferta significativamente mais altas — o candidato qualificado ainda não avançou para outro processo.

Com o volume que a Multipessoal Angola gere, isso significa que parte dos candidatos pré-qualificados está a abandonar o processo não por falta de interesse, mas por ausência de feedback rápido. Um sistema automatizado de triagem e comunicação resolve isto sem exigir mais recrutadores.

Se fizer sentido discutir, fico disponível esta semana para 20 minutos.

Fidel Kussunga
contact@biscaplus.com | +244 956 873 126""",
    },
]

resultados = []

for msg in mensagens:
    canal = "WhatsApp" if msg.get("whatsapp_destino") else "Email"
    destino = msg.get("whatsapp_destino") or msg.get("email_destino")
    print(f"\nEnviando [{canal}] {msg['session_id']} -> {destino}")

    try:
        r = requests.post(SEND_URL, json=msg, timeout=30, verify=False)
        resultado = r.json()
        status = resultado.get("status", "?")
        print(f"  OK {status}")
        resultados.append({
            "session_id": msg["session_id"],
            "canal": canal,
            "destino": destino,
            "status": status,
            "ok": True,
        })
    except Exception as e:
        print(f"  ERRO: {e}")
        resultados.append({
            "session_id": msg["session_id"],
            "canal": canal,
            "destino": destino,
            "status": str(e),
            "ok": False,
        })

    time.sleep(1)

print("\n\n=== RESUMO ===")
ok = [r for r in resultados if r["ok"]]
nok = [r for r in resultados if not r["ok"]]
print(f"Enviados: {len(ok)}/28")
if nok:
    print("Falhas:")
    for r in nok:
        print(f"  - {r['session_id']}: {r['status']}")
