import os
from anthropic import AsyncAnthropic
from app.models import Request

def get_client() -> AsyncAnthropic:
    return AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-6"


async def classify_request(req: Request, lang: str = "es") -> str:
    if lang == "en":
        prompt = f"""Analyze this customer request and provide a classification:

Ticket: {req.ticket_id}
Subject: {req.subject}
Description: {req.description}
Current Type: {req.type}
Current Priority: {req.priority}

Provide:
1. Confirmed or corrected TYPE (petition/complaint/claim/suggestion) with reasoning
2. Confirmed or corrected PRIORITY (low/medium/high/critical) with justification
3. SENTIMENT analysis (positive/neutral/negative/very_negative)
4. DEPARTMENT that should handle this
5. Estimated RESOLUTION TIME in hours
6. Key action items for the agent

Be concise and direct."""
    else:
        prompt = f"""Analiza esta solicitud de cliente y provee una clasificación completa:

Ticket: {req.ticket_id}
Asunto: {req.subject}
Descripción: {req.description}
Tipo actual: {req.type}
Prioridad actual: {req.priority}

Proporciona:
1. TIPO confirmado o corregido (petición/queja/reclamo/sugerencia) con razonamiento
2. PRIORIDAD confirmada o corregida (baja/media/alta/crítica) con justificación
3. Análisis de SENTIMIENTO del cliente (positivo/neutral/negativo/muy negativo)
4. DEPARTAMENTO que debe gestionar este caso
5. TIEMPO DE RESOLUCIÓN estimado en horas
6. Acciones clave para el agente

Sé conciso y directo."""

    msg = await get_client().messages.create(
        model=MODEL,
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text


async def auto_respond(req: Request, lang: str = "es") -> str:
    if lang == "en":
        prompt = f"""Generate a professional, empathetic response to this customer request for our support team to send.

Ticket: {req.ticket_id}
Type: {req.type}
Priority: {req.priority}
Subject: {req.subject}
Description: {req.description}
Customer: {req.customer_name}

Requirements:
- Acknowledge the specific issue
- Show empathy appropriate to the severity
- Explain next steps clearly
- Include realistic timeframe
- Professional but warm tone
- Do NOT use markdown formatting
- 3-4 paragraphs max"""
    else:
        prompt = f"""Genera una respuesta profesional y empática para esta solicitud de cliente que el equipo de soporte enviará.

Ticket: {req.ticket_id}
Tipo: {req.type}
Prioridad: {req.priority}
Asunto: {req.subject}
Descripción: {req.description}
Cliente: {req.customer_name}

Requisitos:
- Reconoce el problema específico del cliente
- Muestra empatía apropiada a la gravedad
- Explica los siguientes pasos con claridad
- Incluye tiempo de respuesta realista
- Tono profesional pero cercano
- NO uses formato markdown
- Máximo 3-4 párrafos"""

    msg = await get_client().messages.create(
        model=MODEL,
        max_tokens=700,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text


async def escalate_case(req: Request, lang: str = "es") -> str:
    if lang == "en":
        prompt = f"""Analyze whether this customer case requires escalation and provide escalation guidance.

Ticket: {req.ticket_id}
Type: {req.type}
Priority: {req.priority}
Status: {req.status}
Sentiment: {req.sentiment}
Subject: {req.subject}
Description: {req.description}
SLA Hours: {req.sla_hours}h

Provide:
1. ESCALATION DECISION: Yes/No with clear reasoning
2. ESCALATION LEVEL: L1 / L2 / Management / Legal / CEO
3. URGENCY: Immediate / Within 4h / Within 24h
4. Specific team or person to escalate to
5. Key information to include in escalation
6. Recommended resolution approach

Be direct and actionable."""
    else:
        prompt = f"""Analiza si este caso de cliente requiere escalación y provee guía de escalación.

Ticket: {req.ticket_id}
Tipo: {req.type}
Prioridad: {req.priority}
Estado: {req.status}
Sentimiento: {req.sentiment}
Asunto: {req.subject}
Descripción: {req.description}
SLA: {req.sla_hours}h

Proporciona:
1. DECISIÓN DE ESCALACIÓN: Sí/No con razonamiento claro
2. NIVEL DE ESCALACIÓN: N1 / N2 / Gerencia / Legal / Dirección
3. URGENCIA: Inmediata / En 4h / En 24h
4. Equipo o persona específica a quien escalar
5. Información clave a incluir en la escalación
6. Enfoque de resolución recomendado

Sé directo y accionable."""

    msg = await get_client().messages.create(
        model=MODEL,
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text


async def summarize_case(req: Request, comments: list, lang: str = "es") -> str:
    comment_text = "\n".join([f"- {c.author}: {c.body[:200]}" for c in comments[:5]])

    if lang == "en":
        prompt = f"""Generate an executive summary of this support case for management review.

Ticket: {req.ticket_id}
Type: {req.type} | Priority: {req.priority} | Status: {req.status}
Customer: {req.customer_name} ({req.customer_email})
Department: {req.department}
Subject: {req.subject}
Description: {req.description}
Interactions: {comment_text or 'None recorded'}

Include:
1. CASE OVERVIEW (2-3 sentences)
2. IMPACT ASSESSMENT (business/customer impact)
3. ACTIONS TAKEN so far
4. CURRENT STATUS and next steps
5. RISK if not resolved quickly
6. RECOMMENDATION for management

Plain text, no markdown."""
    else:
        prompt = f"""Genera un resumen ejecutivo de este caso de soporte para revisión gerencial.

Ticket: {req.ticket_id}
Tipo: {req.type} | Prioridad: {req.priority} | Estado: {req.status}
Cliente: {req.customer_name} ({req.customer_email})
Departamento: {req.department}
Asunto: {req.subject}
Descripción: {req.description}
Interacciones: {comment_text or 'Ninguna registrada'}

Incluye:
1. RESUMEN DEL CASO (2-3 oraciones)
2. EVALUACIÓN DE IMPACTO (impacto en el negocio y cliente)
3. ACCIONES TOMADAS hasta el momento
4. ESTADO ACTUAL y próximos pasos
5. RIESGO si no se resuelve pronto
6. RECOMENDACIÓN para la gerencia

Texto plano, sin markdown."""

    msg = await get_client().messages.create(
        model=MODEL,
        max_tokens=700,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text
