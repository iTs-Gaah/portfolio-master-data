# Corporate Data Management & Extraction Platform

Uma plataforma desenvolvida para resolver problemas de **Governança de Dados, Automação de Rotinas e Controle de Acessos** em ambientes corporativos. O projeto demonstra a integração entre serviços de extração de dados em background e um painel web interativo para os usuários finais.

## 🎯 O Problema de Negócio

Em corporações com grandes volumes de dados operacionais e financeiros, a extração, consolidação e distribuição de informações críticas geralmente sofrem com:
1. **Trabalho Manual e Rotinas Repetitivas:** A dependência de analistas para a execução de consultas (queries) diárias em bancos de dados e a constante atualização manual de planilhas de controle.
2. **Governança e Integridade:** A dificuldade de garantir que os dados consumidos pela operação estão 100% atualizados de maneira centralizada, rastreável e confiável.
3. **Controle de Acessos e Segurança:** O desafio de compartilhar informações gerenciais com segurança, garantindo que cada usuário acesse exclusivamente os painéis referentes à sua área de atuação (silos de permissão).

**A Solução:**
O projeto conta com um **Bot Agendador** rodando em background (24/7) para automatizar rotinas de extração. Ele conecta-se a bases de dados (DW e Datalakes), processa as informações e sincroniza os arquivos finais na nuvem corporativa e no repositório local. Em paralelo, um **Painel de Gestão (Dashboard Web)** consome esses dados com um sistema de autenticação próprio e controle de nível de acesso (RBAC).

## 🏗️ Arquitetura da Solução

A aplicação é inteiramente conteinerizada e dividida em dois serviços principais orquestrados pelo **Docker Compose**:

1. **Bot Extrator (Background Service):**
   - Um serviço construído em Python rodando em loop infinito que dispara pipelines de extração de dados em horários estratégicos ao longo do dia.
   - Conecta-se diretamente aos bancos de dados (ex: MySQL e PostgreSQL), executa queries otimizadas, sanitiza XMLs e lida com conversões de tipagem e formata os dados para exportação performática.
   - Realiza integração via Microsoft Graph API (usando MSAL) para sincronizar os arquivos finais automaticamente em nuvens corporativas.
   - Registra logs detalhados de tempo de execução e controla as datas de atualização (via JSON) para acionar a invalidação de cache do painel web de forma reativa.

2. **Painel de Cadastros (Frontend Application):**
   - Construído em **Streamlit**, projetado com um visual limpo, navegação multipáginas lateral otimizada e foco total em experiência do usuário (UX).
   - Implementa um **Sistema de Autenticação Customizado (Auth):** Validação de credenciais em tempo real, proteção individual de rotas/páginas baseada no perfil do usuário no banco de usuários, e fluxo forçado de primeiro acesso (troca de senha obrigatória).
   - Possui sistema inteligente de invalidação de cache (Data Invalidation) que recarrega as fontes em memória sempre que o Bot Extrator finaliza um ciclo de atualização na base subjacente.
   - Registro automático e rastreamento de acessos globais para futura auditoria e métricas de engajamento (Admin Logs).

## 🛠️ Tecnologias Utilizadas

- **Linguagem Principal:** Python 3.11
- **Orquestração e Deploy:** Docker, Docker Compose
- **Web App / UI:** Streamlit, Altair, Plotly
- **Data Engineering / Manipulação de Dados:** Pandas, openpyxl, SQLAlchemy
- **Bancos de Dados Integrados:** Bancos Relacionais (PostgreSQL, MySQL) consumidos como Data Lakes / Data Warehouses.
- **Integração e Autenticação (Cloud):** MSAL (Microsoft Authentication Library), REST APIs (Microsoft Graph API).

## 🔐 Controle de Acesso e Governança

- **RBAC (Role-Based Access Control):** O acesso a módulos sensíveis ou gerenciais é estritamente controlado. Uma engine de autorização lê dinamicamente as permissões em nuvem, garantindo a restrição do usuário logado.
- **Auditoria de Logs:** Todas as extrações do Bot e todos os logins no sistema geram logs que são monitorados por perfis com acesso `root`/`admin`.
- **Integração Segura:** A autenticação corporativa de serviços (para upload automático) é feita via Client Credentials, garantindo que o pipeline de dados funcione ininterruptamente sem depender de tokens de usuário temporários que poderiam expirar.

## 🚀 Como Rodar Localmente

A plataforma foi arquitetada para ser executada rapidamente em qualquer máquina utilizando containers. É necessário ter o **Docker** e o **Docker Compose** instalados.

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/iTs-Gaah/portfolio-master-data.git
   cd portfolio-master-data
   ```

2. **Configuração de Variáveis de Ambiente:**
   A aplicação depende de diversas variáveis de integração e credenciais de banco. Crie um arquivo `.env` na raiz do projeto (baseado em um `.env.example`), contendo:
   ```ini
   # Conexão DW e Datalake
   DW_HOST=localhost
   DW_USER=usuario_dw
   DW_PASS=senha_dw
   DW_NAME=nome_dw
   DW_PORT=3306

   DB2_HOST=localhost
   DB2_USER=usuario_datalake
   DB2_PASS=senha_datalake
   DB2_NAME=nome_datalake
   DB2_PORT=5432

   # Configurações de API e Segurança
   AZURE_TENANT_ID=xxxx
   AZURE_CLIENT_ID=xxxx
   AZURE_CLIENT_SECRET=xxxx
   ADMIN_USER=admin
   ADMIN_PWD=senha_super_segura
   ```

3. **Subindo os Serviços (Docker Compose):**
   Execute o comando abaixo para compilar as imagens e subir os containers em segundo plano:
   ```bash
   docker-compose up --build -d
   ```

4. **Acessando e Monitorando a Aplicação:**
   - **Dashboard (Painel Web):** Abra seu navegador e acesse `http://localhost:8501`.
   - **Monitoramento do Bot:** Você pode verificar em tempo real as extrações ocorrendo e o tempo de execução através dos logs do container:
     ```bash
     docker logs -f bot_extrator
     ```

## 📈 Impacto no Negócio

- **Redução de Intervenção Humana:** Automatização de ponta a ponta na geração de arquivos estruturados, mitigando falhas e inconsistências manuais.
- **Single Source of Truth (Fonte Única de Verdade):** Os dados disponibilizados no Painel e na nuvem corporativa são sempre reflexos precisos da base de dados no exato momento programado, padronizando os relatórios consumidos pelas áreas de negócio.
- **Performance e Escalabilidade:** A segregação das rotinas de extração (Bot) da visualização (Streamlit) garante que a ferramenta web opere sem lentidão durante o processamento das rotinas pesadas (que envolvem leitura e exportação de dezenas de milhares de linhas para o Excel de forma agrupada).

---
*Aviso: Este repositório serve estritamente como demonstração de habilidades em Engenharia de Dados, Arquitetura de Software e Desenvolvimento em Python. Todos os dados sensíveis, lógicas de negócios específicas da organização, credenciais, URLs corporativas e nomes de sistemas de terceiros foram cuidadosamente removidos ou substituídos por nomenclaturas genéricas e dados ilustrativos para fins de segurança e compliance.*
