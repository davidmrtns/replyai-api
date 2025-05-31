# <img src="https://github.com/davidmrtns/replyai-frontend/blob/main/src/replyai-logo.svg?raw=true" width="28px" /> ReplyAI (API)

![Python](https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue&style=for-the-badge)
![FastAPI](https://img.shields.io/badge/fastapi-109989?style=for-the-badge&logo=FASTAPI&logoColor=white&style=for-the-badge)

## Descrição do projeto
ReplyAI é uma aplicação backend desenvolvida com FastAPI, projetada para atuar como ponte entre assistentes de inteligência artificial e um número de WhatsApp. Seu funcionamento é baseado em uma arquitetura de requisições e respostas: ao receber uma mensagem de um cliente, o sistema aciona um endpoint que processa o conteúdo com uma IA (neste projeto, da OpenAI), que não apenas gera uma resposta em linguagem natural, como também é capaz de **executar rotinas automatizadas** conforme o contexto da conversa.

Isso inclui ações como: consultar ou agendar compromissos, enviar imagens ou vídeos, recuperar informações de sistemas externos, iniciar fluxos personalizados de atendimento e muito mais. Ideal para sistemas de suporte, chatbots avançados ou qualquer aplicação que exija respostas inteligentes aliadas a execução de tarefas automatizadas.

## Funcionalidades
- 💬 **Geração de respostas com IA**: responde automaticamente às mensagens recebidas via WhatsApp usando modelos de linguagem natural;
- 🖼️ **Envio de mídias**: além de mensagens de texto, a API pode enviar imagens, vídeos e documentos pré-cadastrados, além de responder em áudio caso receba uma mensagem de voz;
- 📅 **Agendamentos**: a API se integra com Outlook e Google Agenda para cadastrar agendamentos, consultar horários livres na agenda e sugerí-los aos clientes;
- 💸 **Gestão de cobranças**: envio automatizado de mensagens de cobrança para clientes inadimplentes;
- ⏰ **Lembretes de vencimento**: notifica automaticamente os clientes sobre parcelas próximas do vencimento, de acordo com integração com Asaas.
- 🙏 **Mensagens de agradecimento**: envia mensagens automáticas de agradecimento após o pagamento dos boletos.
- 📄 **Envio de notas fiscais**: encaminha as notas fiscais emitidas via Asaas diretamente para o cliente;
- 🤖 **Gestão da aplicação**: a API conta com endpoints para gestão completa do funcionamento da ferramenta.

### Integrações
| Categoria                  | Ferramentas/Serviços                         | Finalidade                                                   |
|----------------------------|----------------------------------------------|---------------------------------------------------------------|
| 📅 **Calendários virtuais**| Google Agenda, Outlook                       | Agendamento automático de compromissos                        |
| 💬 **WhatsApp API**        | Digisac, EvolutionAPI                        | Envio e recebimento de mensagens                              |
| 📊 **CRM**                 | RD Station CRM                               | Registro e gerenciamento de leads                             |
| 🤖 **Geração de respostas**| OpenAI (Assistants API)                      | Geração de respostas inteligentes                             |
| 🔉 **Respostas em áudio**  | ElevenLabs                                   | Conversão de texto em áudio natural                           |
| ☁️ **Armazenamento**       | Azure Blob Storage                           | Armazenamento de imagens, vídeos e outros arquivos gerados    |

## Desenvolvimento
### Tecnologias utilizadas
- **Backend**: FastAPI;
- **Integração de IA**: OpenAI;
- **Banco de dados**: SQLAlchemy.

## Autor
- David Martins - [@davidmrtns](https://github.com/davidmrtns/)
