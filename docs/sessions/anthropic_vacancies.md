---
title: "Вакансии Anthropic по кластерам"
slug: "anthropic_vacancies"
q6: "100101"
exchanges: 1
source: "claude.ai session export"
---

# Вакансии Anthropic по кластерам

<!-- ======================================================================
NAUTILUS INTEGRATION NOTE
========================================================================

Этот файл автоматически индексируется ConversationAdapter (adapters/conversation.py).
Зарегистрируйте папку docs/sessions/ один раз:

    from adapters.conversation import ConversationAdapter
    portal.register("sessions", ConversationAdapter("docs/sessions/"))

После этого файл будет доступен через стандартный API:

    # TF-IDF семантический поиск по всем сессиям:
    python tfidf_search.py --build-index
    python tfidf_search.py "{тема}"

    # REST API (после запуска api.py):
    GET /api/query?q={тема}&ranked=1

    # Консенсус с основной базой знаний:
    portal.query("{концепт}")   # сравнивает с info1, pro2, meta, data2, data7

    # Прямая работа:
    adapter = ConversationAdapter("docs/sessions/")
    results = adapter.fetch("{запрос}")
    for r in results:
        print(r.title, r.metadata["q6"])

======================================================================= -->

---

## Обмен 1

**Вопрос:**

https://3dnews.ru/1140248/glava-anthropic-predryok-ischeznovenie-inzhenernykh-professiy-i-otkryl-429-vakansiy-s-zarplatoy-do-405000 подробнее про вакансии которые есть краткое описание по кластерам

---

**Ответ:**

Статья даёт только общие цифры (≈429 вакансий, вилка $320–405 тыс.) и называет буквально пару примеров должностей. Чтобы сделать разбивку по кластерам — сходим прямо на страницу вакансий Anthropic.

Сходил на официальную страницу вакансий Anthropic — там сейчас **436 открытых ролей** (цифра плавает ежедневно, статья зафиксировала ≈429). Важная поправка к формулировке журналиста: это **все открытые позиции компании**, а не «429 разработчиков» — инженерных из них примерно 40–45%. Раскладка по 16 официальным кластерам:

## AI Research & Engineering — 68 ролей
Ядро исследовательского и ML-инженерного найма. Research Engineer/Scientist по направлениям Pre-training, Post-training, RL, Interpretability, Alignment Science, Frontier Red Team (Cyber/Autonomy/Emerging Risks), Vision, Audio, Agents, Reward Models, Science of Scaling, Economic Research. Отдельно — Anthropic Fellows Program (AI Safety, AI Security, ML Systems & Performance, RL). Сюда же TPU Kernel Engineer, Performance Engineer GPU, инженерные менеджеры Inference/GPU. Именно здесь «вилка до $405K» осмысленна.

## Sales — 150 ролей (самый большой кластер, ≈34% всего найма)
То, что статья замалчивает: основной рост Anthropic сейчас — не в инженерах, а в GTM. Account Executive (Enterprise, Strategic, Mid-Market, SMB, Startups, Federal, State & Local, DOD/IC), Solutions Architect Applied AI по вертикалям (Industries, Life Sciences, Financial Services, Government, National Security, Digital Native, Startups), Forward Deployed Engineer (та самая роль, которую Амодеи называет «новой специальностью»), Customer Success Manager, Business Development Representative, Partner Managers под GSI и Systems Integrators. География — SF, NY, London, Dublin, Munich, Paris, Tokyo, Seoul, Bangalore, Sydney, Zurich.

## Finance — 36 ролей
Очень активно растёт: Revenue Accounting (включая новый Senior Manager по New Product Introduction), Deal Desk и Deal Operations по трём регионам (Americas/APAC/EMEA), Treasury, Payroll, Tax, Finance Systems Engineer, Director Technical Accounting M&A. Сигнал: компания готовится к бóльшему операционному масштабу и возможным M&A/инвестрелейшенс событиям (есть отдельная роль Capital Markets & Investor Relations).

## Security — 24 роли
Application Security, Detection & Response, Offensive Security, Insider Risk, Platform Hardware Security, eBPF & Security Sensors, GRC Engineering, HIPAA Compliance, Crisis Management, Geopolitical Intelligence Analyst. Кластер насыщен именно инженерными ролями — не «корпоративной охраной».

## Marketing & Brand — 23 роли
Art Director Enterprise, Copy Leads, Customer Marketing (включая Startup Marketing EMEA), Field Marketing, Partner Marketing, Segment Marketing по вертикалям (Financial Services & Insurance, Strategic Accounts), Video Director Product Launches, Developer Community Lead EMEA. Отражает переход от «research lab» к продуктовой компании с B2B-воронкой.

## Engineering & Design - Product — 22 роли
Продуктовая инженерия: Software Engineer (Full-stack, Backend, Platform, UI, iOS, Android, Desktop), Staff+ уровни, Product Designer Claude Code, Prompt Engineer, Model Quality Engineer, API (Senior Staff), Billing Platform, Cybersecurity Products, Auth & Identity. Это ваши коллеги по стеку Managed Agents API / Claude Code.

## Software Engineering - Infrastructure — 22 роли
Inference (самая частая роль — 8+ позиций разного уровня в SF/London/Dublin/Seattle), Cloud Inference AWS, Sandboxing, AI Reliability, Data Infrastructure, Databases, Observability, Voice Platform, Datacenter Server Lifecycle, Developer Productivity. Фактически — команда, которая обслуживает то, на чём вы крутите свои proxy на Termux.

## Safeguards (Trust & Safety) — 21 роль
Trust & Safety в ML-смысле: Biological Safety Research Scientist, Policy Manager по CBRN-E (Chemical/Biological/Radiological/Nuclear/Explosives), Offensive Security Research Engineer, Threat Investigators (CBRN-E, Cyber, Influence Operations), Safeguards Analysts (Account Abuse, Human Exploitation, Fraud & Scams), Age-Appropriate Design Policy Manager. Кластер объясняет недавний анонс «ИИ по паспорту» для Claude.

## Product Management, Support, & Operations — 17 ролей
Product Manager по Claude Code, API Growth, Consumer, Monetization, Multi-Cloud Growth - Google, Research Product; Product Operations Manager (Feedback Loops, Research Product); Product Support Specialist/Manager (US + Dublin + Tokyo).

## Compute — 13 ролей
Чисто «железная» инфраструктура: Data Center Engineers (Electrical, Capacity Delivery, Portfolio Planning, Resource Efficiency), Network Engineer, Cluster Deployment Engineer, Transaction Principal/Manager (закупка/аренда мощностей в US/UK/Australia). Отдельная роль Strategic Deals Lead, Compute & Infrastructure — показатель масштаба контрактов с облаками.

## Legal — 13 ролей
Commercial Counsel по поднаправлениям (Colocation & Networks, Datacenters & Construction, Compute & Infrastructure, EMEA, GTM), Frontier Counsel (регуляторика передовых моделей), Trade Compliance Counsel, Product Counsel Claude Platform, People Legal. Юридический стек заточен под инфраструктурные сделки + экспортный контроль.

## Technical Program Management — 10 ролей
TPM по Alignment, Compute, Inference Performance, Infrastructure, Platform, Safeguards (Infrastructure & Evals), Security, Consumer Engineering, Marketing Tech. Классический coordinator-слой между ML research и shipping.

## Communications — 5 ролей
Communications Lead для Claude Code и для Anthropic Institute, Communications Manager Research, Engineering Editorial Lead, Internal Communications Manager Policy.

## Public Policy — 5 ролей
External Affairs Australia, Policy Analyst LATAM, Policy Planning & Operations US Federal, Political Programs Manager, Solutions Architect National Security (все вне SF — DC, Canberra).

## Public Benefit — 4 роли
Новый Anthropic Institute (объявлен 11 марта 2026): Analyst, Research Economist, Transformative AI Research Economist, Research Operations — объединяет Frontier Red Team, Societal Impacts, Economic Research.

## People — 3 роли
Immigration Coordinator, People Operations Lead, Technical Recruiter. Маленький кластер — значит, рекрутинговая машина в целом уже собрана.

---

**Что реально говорит эта структура.** Тезис Амодеи «кодинг исчезнет первым» и открытый найм 68 Research Engineer'ов — не противоречие, а сигнал о том, *какие именно* инженерные роли остаются: не «написать CRUD», а те, что на переднем крае самой модели (pre-training, RL, alignment, interpretability, inference performance на GPU/TPU). Самый быстрорастущий блок — вовсе не разработка, а **Sales + Applied AI (≈200 ролей вместе с Forward Deployed Engineer)**. Это и есть та самая «новая специальность» из статьи, только масштабированная: компания строит вертикаль внедрения в отрасли (финансы, здравоохранение, госсектор, life sciences, manufacturing) и в гео (EMEA, APAC, India). Вилка $320–405K из статьи применима реально только к верхней части AI Research & Engineering и Staff+ SWE — в Sales/Finance/Marketing/Legal зарплаты ниже и сильно варьируются по локации.

Если нужно — могу выгрузить полный список ролей в CSV или XLSX для вашей аналитики, либо отфильтровать под конкретный профиль (например, роли, релевантные вашему стеку: Managed Agents API, agents, RL, MoME-подобные архитектуры).

---

---
