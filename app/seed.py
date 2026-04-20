from datetime import datetime, timedelta
import random
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import User, Request, Comment
from app.auth import hash_password

CUSTOMERS = [
    ("María García", "maria.garcia@email.com", "+57 310 555-0101"),
    ("Carlos Rodríguez", "c.rodriguez@empresa.co", "+57 315 555-0202"),
    ("Ana Martínez", "ana.m@hotmail.com", "+52 55 5555-0303"),
    ("Luis Hernández", "l.hernandez@corp.mx", "+52 55 5555-0404"),
    ("Sofia López", "sofia.lopez@gmail.com", "+34 612 555-0505"),
    ("Diego Pérez", "d.perez@negocios.es", "+34 612 555-0606"),
    ("Valentina Torres", "v.torres@email.com", "+57 320 555-0707"),
    ("Roberto Sánchez", "r.sanchez@tech.io", "+1 305 555-0808"),
    ("Isabella Ramírez", "isa.ramirez@outlook.com", "+52 81 5555-0909"),
    ("Andrés Flores", "a.flores@empresa.co", "+57 300 555-1010"),
    ("Camila Vargas", "c.vargas@mail.com", "+34 611 555-1111"),
    ("Javier Castro", "j.castro@business.com", "+1 786 555-1212"),
    ("Lucía Moreno", "lucia.m@personal.es", "+34 613 555-1313"),
    ("Sebastián Jiménez", "s.jimenez@corp.mx", "+52 33 5555-1414"),
    ("Natalia Romero", "n.romero@email.co", "+57 311 555-1515"),
]

REQUESTS_DATA = [
    # Petitions
    ("petition", "Solicitud de certificado de servicio", "Requiero un certificado oficial que acredite mi suscripción activa al servicio premium desde enero 2024. Lo necesito para presentar ante mi empresa como comprobante de beneficio laboral.", "Soporte Técnico", "low", "resolved", "positive", 24),
    ("petition", "Actualización de datos de facturación", "Necesito actualizar la información fiscal de mi cuenta. Mi empresa cambió de razón social y requiero que las facturas se emitan con los nuevos datos antes del cierre del mes.", "Facturación", "medium", "resolved", "neutral", 48),
    ("petition", "Solicitud de historial de transacciones", "Por favor envíen el historial completo de transacciones de los últimos 12 meses. Necesito este reporte para una auditoría interna programada para la próxima semana.", "Facturación", "medium", "in_progress", "neutral", 48),
    ("petition", "Acceso a módulo de reportes avanzados", "Solicito acceso al módulo de análisis avanzado incluido en mi plan Enterprise. Según el contrato firmado hace 3 meses, debería tener acceso pero aún no aparece habilitado.", "Soporte Técnico", "high", "open", "neutral", 24),
    # Complaints
    ("complaint", "Servicio caído por más de 4 horas", "La plataforma estuvo completamente inaccesible desde las 9 AM hasta la 1 PM del día de hoy. Esto nos causó pérdidas significativas ya que no pudimos procesar ninguna orden de venta durante ese período.", "Operaciones", "critical", "escalated", "very_negative", 4),
    ("complaint", "Cobro duplicado en mi tarjeta", "Revisando mi estado de cuenta encontré dos cargos del mismo monto en el mismo día. Exijo la devolución inmediata del cargo duplicado y una explicación de por qué ocurrió esto.", "Facturación", "high", "in_progress", "very_negative", 24),
    ("complaint", "Soporte técnico no responde desde hace 3 días", "Abrí un ticket hace 3 días con un problema crítico de integración API y nadie me ha respondido. Mi equipo de desarrollo está bloqueado esperando la solución.", "Soporte Técnico", "critical", "escalated", "very_negative", 4),
    ("complaint", "Funcionalidad de exportación no funciona", "Desde la última actualización del sistema, el botón de exportar a Excel simplemente no hace nada. He probado en diferentes navegadores y el problema persiste.", "Soporte Técnico", "high", "resolved", "negative", 24),
    ("complaint", "Tiempo de respuesta del chat inaceptable", "El chat de soporte en vivo promete respuesta en menos de 2 minutos pero he esperado más de 45 minutos en dos ocasiones esta semana sin que nadie me atienda.", "Servicio al Cliente", "medium", "open", "negative", 48),
    # Claims
    ("claim", "Reembolso por servicio no prestado", "Durante el mes de marzo el módulo de BI no funcionó correctamente durante 8 días hábiles. Según los términos del SLA, corresponde un crédito del 30% sobre el monto mensual.", "Facturación", "high", "in_progress", "negative", 48),
    ("claim", "Compensación por pérdida de datos", "Una actualización del sistema eliminó registros históricos de nuestra base de datos. Tenemos backups hasta hace 3 semanas pero perdimos datos críticos de las últimas 3 semanas.", "Operaciones", "critical", "escalated", "very_negative", 4),
    ("claim", "Descuento prometido no aplicado", "El vendedor me ofreció un 25% de descuento por renovación anticipada pero la factura llegó sin el descuento aplicado. Tengo el email donde se prometió el beneficio.", "Facturación", "medium", "resolved", "negative", 48),
    ("claim", "Características del plan no coinciden con lo vendido", "Me vendieron el plan Business con integración nativa con Salesforce pero al activar la cuenta descubro que esa integración cuesta extra. Exijo el precio acordado o la cancelación sin penalidad.", "Ventas", "high", "open", "very_negative", 24),
    # Suggestions
    ("suggestion", "Agregar modo oscuro a la interfaz", "Trabajo muchas horas con la plataforma y la interfaz blanca me cansa la vista. Sería excelente contar con un modo oscuro como opción. Muchos usuarios en el foro también lo están pidiendo.", "Producto", "low", "resolved", "positive", 72),
    ("suggestion", "Integración con WhatsApp Business API", "Sería muy útil poder responder solicitudes de clientes directamente desde WhatsApp dentro de la plataforma. Muchos de nuestros clientes prefieren ese canal.", "Producto", "medium", "open", "positive", 72),
    ("suggestion", "Dashboard personalizable con widgets", "Permitir que cada usuario configure su propio dashboard con los KPIs más relevantes para su rol haría la herramienta mucho más eficiente.", "Producto", "low", "open", "positive", 72),
    ("suggestion", "Exportar reportes en formato PDF automáticamente", "Actualmente los reportes solo se pueden exportar manualmente. Sería ideal poder programar envíos automáticos por email en formato PDF cada semana o mes.", "Producto", "medium", "in_progress", "positive", 72),
    ("suggestion", "App móvil con notificaciones push", "Uso la plataforma desde el celular frecuentemente pero la versión web no está optimizada. Una app nativa con notificaciones en tiempo real sería muy valiosa.", "Producto", "medium", "open", "neutral", 72),
]

CHANNELS = ["web", "email", "phone", "chat"]
AGENTS = ["Laura Gómez", "Carlos Vega", "Ana Torres", "Miguel Ríos", "Sin asignar"]

AI_RESPONSES = {
    "petition": "Estimado cliente, hemos recibido su solicitud y la estamos procesando. Nuestro equipo revisará su caso y le responderá en el plazo indicado. Si necesita información adicional, no dude en contactarnos.",
    "complaint": "Lamentamos profundamente los inconvenientes que ha experimentado. Su satisfacción es nuestra prioridad y estamos trabajando para resolver esta situación a la brevedad posible. Le mantendremos informado del progreso.",
    "claim": "Hemos registrado su reclamo y lo estamos revisando con el equipo correspondiente. Nos comprometemos a darle una respuesta formal con la solución o compensación que corresponda dentro del plazo establecido.",
    "suggestion": "¡Gracias por su sugerencia! Valoramos enormemente el feedback de nuestros clientes. Hemos registrado su propuesta y la compartiremos con nuestro equipo de producto para su evaluación en el próximo ciclo de desarrollo.",
}


async def seed_database(db: AsyncSession):
    existing = (await db.execute(select(User))).scalar_one_or_none()
    if existing:
        return

    user = User(email="demo@projectsfactory.io", password_hash=hash_password("demo123"), name="Demo User")
    db.add(user)

    now = datetime.utcnow()
    req_objects = []

    for i, (rtype, subject, description, dept, priority, status, sentiment, sla) in enumerate(REQUESTS_DATA):
        customer = CUSTOMERS[i % len(CUSTOMERS)]
        days_ago = random.randint(0, 30)
        created = now - timedelta(days=days_ago, hours=random.randint(0, 23))
        resolved_at = None
        if status in ("resolved", "closed"):
            resolved_at = created + timedelta(hours=random.randint(2, sla))

        req = Request(
            ticket_id=f"PQR-{2026001 + i}",
            type=rtype,
            channel=CHANNELS[i % len(CHANNELS)],
            subject=subject,
            description=description,
            customer_name=customer[0],
            customer_email=customer[1],
            customer_phone=customer[2],
            department=dept,
            priority=priority,
            status=status,
            sentiment=sentiment,
            ai_response=AI_RESPONSES[rtype],
            assigned_to=AGENTS[i % len(AGENTS)],
            sla_hours=sla,
            created_at=created,
            updated_at=created,
            resolved_at=resolved_at,
            is_escalated=(status == "escalated"),
        )
        db.add(req)
        req_objects.append((req, created))

    await db.flush()

    for req, created in req_objects:
        comment = Comment(
            request_id=req.id,
            author="AI Agent",
            body=AI_RESPONSES[req.type],
            is_internal=False,
            created_at=created + timedelta(minutes=random.randint(5, 60)),
        )
        db.add(comment)

    await db.commit()
