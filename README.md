# Feed de Oportunidades 🚀

Um web scraper híbrido (RSS + HTML) construído em Python que monitora diariamente páginas de editais de institutos federais, universidades e fundações de apoio, enviando alertas de novas oportunidades direto no Telegram.

Evolução do projeto [Rss2Telegram](https://github.com/redmagikarp13/Rss2Telegram).

## 🌟 Funcionalidades

- **Abordagem Híbrida**: Tenta ler os feeds RSS primeiro. Se falharem (como muitos sites institucionais costumam fazer), faz web scraping da página HTML como fallback automático.
- **+30 Fontes Monitoradas**: Foco no IFES, UFES, FACTO, grandes universidades federais, agências de fomento e fundações de apoio.
- **Bot no Telegram**: Notificações formatadas e com emojis organizados por categoria.
- **Primeira Execução Silenciosa**: Para evitar spam de dezenas de mensagens na primeira execução, o bot cadastra todo o histórico atual silenciosamente.
- **Serverless**: Projetado para rodar gratuitamente via GitHub Actions com persistência usando artefatos para o SQLite.

## 🛠️ Instalação Local

1. Clone o repositório e instale as dependências:
```bash
git clone https://github.com/SEU_USUARIO/feedOportunid.git
cd feedOportunid
pip install -r requirements.txt
```

2. Crie os arquivos de configuração na raiz (`BOT_TOKEN.txt` e `DESTINATION.txt`) ou use um arquivo `.env` (baseado no `.env.example`).
   - `BOT_TOKEN`: O token da API fornecido pelo @BotFather no Telegram.
   - `DESTINATION`: O Chat ID (ou ID do Canal/Grupo) onde as mensagens serão enviadas.

3. Execute o monitoramento:
```bash
python src/main.py
```

### Dry Run (Modo de Teste)
Para testar a varredura sem enviar mensagens reais pro Telegram, crie um arquivo `DRYRUN.txt` contendo a palavra `true` ou defina a variável de ambiente `DRYRUN=true`.

## 🤖 Como rodar no GitHub Actions

1. Suba este código para o seu repositório no GitHub.
2. Vá na aba **Settings** > **Secrets and variables** > **Actions** > **New repository secret**.
3. Crie duas variáveis:
   - `BOT_TOKEN`: com o valor do seu token do Telegram.
   - `DESTINATION`: com o Chat ID do grupo de destino.
4. O GitHub Actions rodará automaticamente todos os dias de manhã! Você também pode disparar manualmente na aba **Actions**.

## 🏗️ Estrutura do Código

- `src/config.py`: Lista de todos os 34+ sites e variáveis de ambiente.
- `src/scraper.py`: Motor de requisições Híbrido (RSS / BeautifulSoup).
- `src/storage.py`: Banco de dados SQLite persistente para não repetir editais.
- `src/notifier.py`: Envio de mensagens formatadas pro Telegram.
- `src/parsers/`: Scripts modulares para sites que precisam de CSS selectors complexos (FACTO, UFMG, Gov.br, etc).
