## C1 – Contexto
```mermaid
C4Context
    title PromptShield - Contexto
    Person(user, "Usuário", "Envia perguntas via HTTP para o sistema.")
    System_Boundary(ps, "PromptShield API") {
        System(ps_api, "FastAPI App", "Firewall semântico + orquestração do LLM")
    }
    System_Ext(gemini, "Gemini API (Google GenAI)", "LLM de geração de respostas")
    System_Ext(storage, "File System / Artefatos", "Datasets, modelos e logs")

    Rel(user, ps_api, "HTTP /chat")
    Rel(ps_api, gemini, "generateContent() via SDK")
    Rel(ps_api, storage, "Lê/escreve")

C4Container
    title PromptShield - Contêineres
    Person(user, "Usuário")

    System_Boundary(ps, "PromptShield") {
        Container(api, "FastAPI App", "Python/FastAPI", "Exposição de endpoints")
        Container(decision, "DecisionEngine", "Python", "Agrega classificadores + Policy")
        Container(classifiers, "Classificadores", "Python", "Rule-based + SBERT")
        Container(sanitizer, "LLMSanitizer", "Python", "Reescreve/normaliza prompts")
        Container(gemini_client, "GeminiClient", "Python", "Adapter para Google GenAI SDK")
        ContainerDb(data, "Data/Models/Logs", "File System", "datasets, modelos, logs")
    }

    System_Ext(gemini, "Gemini API", "Google GenAI")

    Rel(user, api, "HTTP /chat")
    Rel(api, decision, "evaluate(message)")
    Rel(decision, classifiers, "predict()")
    Rel(api, sanitizer, "sanitize() se necessário")
    Rel(api, gemini_client, "generateContent()")
    Rel(gemini_client, gemini, "Chamada LLM")
    Rel(api, data, "leitura/escrita")

C4Component
    title PromptShield - Componentes principais (/chat)
    Container_Boundary(api, "FastAPI App") {
        Component(handler, "ChatHandler", "app.py", "Recebe request /chat")
        Component(logging, "Logger", "logging_setup.py", "Logs estruturados JSON")
    }
    Container_Boundary(app, "Aplicação") {
        Component(engine, "DecisionEngine", "decision_engine.py", "Agrega classificadores + Policy")
        Component(policy, "Policy", "policy.py", "Regras de thresholds")
    }
    Container_Boundary(adapters, "Adaptadores") {
        Component(rb, "RuleBasedClassifier", "rule_based_classifier.py")
        Component(sbert, "SBertClassifier", "sbert_classifier.py")
        Component(sanit, "LLMSanitizer", "llm_sanitizer.py")
        Component(gemcli, "GeminiClient", "gemini_client.py")
    }
    Container_Boundary(data, "Dados/Artefatos") {
        Component(dataset, "Datasets", "data/*")
        Component(models, "Modelos", "models/*")
        Component(logs, "Logs", "logs/*")
    }
    System_Ext(gemini, "Gemini API (Google GenAI)")

    Rel(handler, engine, "evaluate()")
    Rel(engine, rb, "predict()")
    Rel(engine, sbert, "predict()")
    Rel(engine, policy, "usa thresholds")
    Rel(handler, sanit, "sanitize()")
    Rel(handler, gemcli, "generateContent()")
    Rel(gemcli, gemini, "chamada LLM")
    Rel(handler, logs, "registra métricas")

