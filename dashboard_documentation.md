# Documentação do Dashboard de Informativos STF (V17 - Funcionalidades Adicionais)

## Visão Geral

Este dashboard interativo, desenvolvido com Streamlit, permite a exploração e análise dos Informativos de Jurisprudência do Supremo Tribunal Federal (STF) compilados a partir do arquivo `Dados_InformativosSTF_2021-2025.xlsx`. O objetivo é fornecer uma ferramenta para estudo e consulta dos julgados, com funcionalidades adicionais **integradas via API (RESULT)** para auxiliar na fixação do conteúdo e organização dos estudos.

**Novidades da Versão V17:**

*   **Filtros em Metas:** A aba "Metas de Leitura" agora possui filtros por "Mês/Ano do Julgamento" e "Ramo do Direito" para refinar a seleção aleatória.
*   **Ajustes de Estilo:** O texto em elementos com fundo amarelo (cor primária `#E8C061`), como botões de rádio selecionados e tags de multiseleção, agora é preto para melhor contraste.
*   **Tradução:** Placeholders como "Choose an option" foram traduzidos para "Selecione uma opção".
*   **Terminologia:** Menções a "IA" ou "ChatGPT" foram substituídas pelo termo genérico "RESULT".
*   **Posicionamento da Logo:** A logo agora aparece no topo da barra lateral (após login) e também centralizada acima das abas na seção principal "Informativos". Na tela de login/registro, a logo também está centralizada.
*   **Registro de Atividades:** As principais ações do usuário (login, logout, registro, marcar/desmarcar leitura, gerar meta) são registradas no arquivo `activity_log.csv` para fins de acompanhamento.
*   **Relatório Diário (Script):** Um script `generate_daily_report.py` (a ser criado) pode ser usado para gerar um resumo diário das atividades a partir do log.

**IMPORTANTE:** As funcionalidades de "RESULT" (Assertivas, Perguntas, Caso Prático) requerem uma chave de API da OpenAI configurada nos segredos (`secrets`) da sua aplicação no Streamlit Community Cloud. Veja a seção "Configuração da API (RESULT)" abaixo.

## Funcionalidades Principais (V17)

O dashboard está organizado em abas e possui uma barra lateral para filtros avançados, acessíveis após o login.

### 1. Login e Registro de Usuário (Sistema Personalizado)

- **Tela Inicial:** Ao acessar o dashboard, você verá as abas "Login" e "Registrar", com a logo centralizada acima.
- **Registro:** Novos usuários podem ir até a aba "Registrar", preencher nome de usuário, nome para exibição e senha (com confirmação) para criar uma conta. As credenciais são salvas de forma segura (senha com hash usando `bcrypt`) no arquivo `user_credentials.json` da aplicação.
- **Login:** Usuários registrados podem ir até a aba "Login", inserir seu nome de usuário e senha para acessar o dashboard. A sessão é gerenciada usando `st.session_state`.
- **Logout:** Um botão "Logout" está disponível na barra lateral após o login.

### 2. Carregamento e Processamento de Dados

- Os dados são carregados a partir do arquivo Excel `Dados_InformativosSTF_2021-2025.xlsx`.
- **Apenas as seguintes colunas são consideradas**, conforme especificado anteriormente:
    - `Informativo`, `Classe Processo`, `Data Julgamento`, `Título`, `Tese Julgado`, `Resumo`, `Ramo Direito`, `Matéria`, `Repercussão Geral`, `Tema RG`, `Legislação`, `Notícia Completa`.
- O processo inclui mapeamento flexível de colunas, limpeza, conversão de tipos, extração de datas, processamento de `Ramo Direito` (explode), tratamento de valores ausentes.

### 3. Barra Lateral (Pós-Login)

- **Logo:** Exibida no topo da barra lateral.
- **Boas-vindas e Logout:** Exibe o nome do usuário logado e o botão de logout.
- **Filtros Avançados:**
    - Filtrar Data Por: Ano ou Mês/Ano.
    - Ano do Julgamento: Seleção múltipla.
    - Mês/Ano do Julgamento: Seleção múltipla (placeholder traduzido).
    - Ramo do Direito: Seleção múltipla (placeholder traduzido).
    - Classe Processual: Seleção múltipla (placeholder traduzido).
    - Repercussão Geral: Seleção única.
    - **Mostrar Apenas Não Lidos:** Checkbox.
- **Contador:** Exibe contagem de julgados únicos filtrados.

### 4. Aba "🔍 Informativos"

- **Logo:** Exibida centralizada acima do título da aba.
- **Busca por Palavra-Chave:** Busca em `Título` e `Matéria`.
- **Cards:** Exibem detalhes do julgado com estilo moderno, **botão de Marcar como Lido/Não Lido (📖/✅)**, e botões de ação ("Gerar Assertiva (RESULT)", "Gerar Caso Prático (RESULT)"). Os títulos são exibidos corretamente sem `**`.
- **Funcionalidade Leitura (por Usuário):** Clicar no botão 📖/✅ alterna o status de leitura do julgado *para o usuário logado*. O status é salvo e recuperado automaticamente.
- **Funcionalidade "Caso Prático" (Integrado API - RESULT):** Gera caso prático baseado na `Notícia Completa`.

### 5. Aba "✅ Assertivas" (Integrado API - RESULT)

- Gera assertivas Certo/Errado com gabarito baseado no `Resumo` do julgado selecionado.

### 6. Aba "❓ Perguntas" (Integrado API - RESULT)

- Responde perguntas sobre **um julgado específico selecionado**. Para usar, primeiro clique no botão "Fazer Pergunta (RESULT)" no card do julgado desejado na aba "Informativos". Em seguida, vá para a aba "Perguntas", onde o contexto do julgado selecionado será exibido, e você poderá inserir sua pergunta sobre ele.

### 7. Aba "🎯 Metas de Leitura"

- Permite gerar metas de leitura aleatórias com base em filtros.
- **Novos Filtros:** Adicionados filtros por "Mês/Ano do Julgamento" e "Ramo do Direito" para refinar a seleção da meta.
- Os cards exibidos na meta também possuem o botão de Marcar como Lido/Não Lido.

## Armazenamento de Dados do Usuário

- **Credenciais:** As informações de login (usuário, nome para exibição, hash da senha `bcrypt`) são armazenadas no arquivo `user_credentials.json`.
- **Dados de Leitura:** Para cada usuário que marca um informativo como lido, um arquivo `[username].pkl` é criado na pasta `user_data`. Este arquivo armazena o conjunto de IDs dos informativos marcados como lidos por aquele usuário.

## Registro de Atividades e Relatório Diário

- **Log de Atividades:** O arquivo `activity_log.csv` registra automaticamente as seguintes ações com timestamp, usuário e detalhes:
    - Login
    - Logout
    - Registro de novo usuário
    - Marcar julgado como lido
    - Marcar julgado como não lido
    - Geração de meta de leitura (com filtros aplicados)
- **Script de Relatório Diário (`generate_daily_report.py` - *a ser criado*):**
    - Este script (que será fornecido separadamente) processará o `activity_log.csv` para gerar um resumo diário das atividades (ex: logins únicos, julgados mais lidos, etc.).
    - **Agendamento:** Devido a limitações do ambiente de desenvolvimento, o agendamento automático (ex: envio diário por email) não pode ser configurado aqui. Você precisará configurar a execução periódica deste script no seu ambiente de produção (servidor ou Streamlit Cloud) usando ferramentas como `cron` (Linux/macOS), Agendador de Tarefas (Windows) ou serviços de agendamento em nuvem. O envio do CSV gerado por email também precisará ser configurado separadamente usando ferramentas de linha de comando ou APIs de serviço de email.

## Personalização Visual (Estilo)

- **Tema:** Escuro (fundo preto, texto branco, detalhes em dourado `#E8C061`).
- **Fonte:** Montserrat.
- **Logo:** Exibida no topo da barra lateral e centralizada na aba "Informativos" e na tela de login.
- **Cards:** Estilo "3D".
- **Botões:** Texto em **preto e negrito** sobre fundo dourado.
- **Contraste:** Texto em elementos com fundo `#E8C061` (cor primária) agora é preto.

### Como Personalizar o Estilo:

A aparência é controlada por `stf_dashboard/.streamlit/config.toml` (cores base) e `stf_dashboard/style.css` (estilos detalhados).

## Configuração da API (RESULT)

(Instruções permanecem as mesmas - configurar `OPENAI_API_KEY` nos segredos do Streamlit Cloud).

## Execução Local

1.  Descompacte o arquivo `.zip`.
2.  Navegue até a pasta `stf_dashboard` pelo terminal.
3.  Instale as dependências: `pip install -r requirements.txt` (Note que `streamlit-authenticator` foi removido e `bcrypt`, `logging` foram adicionados/utilizados).
4.  (Opcional, para teste local do RESULT) Crie `.streamlit/secrets.toml` com sua chave OpenAI.
5.  Execute o dashboard: `streamlit run app.py`

*Nota: Os arquivos `style.css`, `logo.png`, `Dados_InformativosSTF_2021-2025.xlsx`, a pasta `.streamlit` devem estar dentro da pasta `stf_dashboard`. Os arquivos `user_credentials.json`, `activity_log.csv` e a pasta `user_data` serão criados automaticamente no primeiro uso.*

