from app.jobs.implementations.recall_conversations import RecallConversationsJob
from app.jobs.implementations.confirm_appointments import ConfirmAppointmentsJob
from app.jobs.implementations.charge_defaulters import ChargeDefaultersJob
from app.jobs.implementations.notify_due_dates import NotifyDueDatesJob


JOBS = {
    "recall_conversations": RecallConversationsJob,
    "confirm_appointments": ConfirmAppointmentsJob,
    "charge_defaulters": ChargeDefaultersJob,
    "notify_due_dates": NotifyDueDatesJob,
}
