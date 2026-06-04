# Legacy serializers (existing Incident/Change models)
from .legacy import (
    ServiceCategorySerializer, ServiceCategoryCreateUpdateSerializer,
    SlaPolicySerializer,
    IncidentSerializer, IncidentCreateUpdateSerializer,
    ChangeSerializer, ChangeCreateUpdateSerializer,
    ServiceRequestSerializer,
    ProblemSerializer, ProblemCreateUpdateSerializer,
)
# New workflow engine serializers
from .workflow_serializers import (
    WorkflowSerializer, WorkflowCreateSerializer,
    WorkflowVersionSerializer,
    StateSerializer, TransitionSerializer, FieldSerializer,
)
from .ticket_serializers import (
    TicketSerializer, TicketCreateSerializer, TicketSubmitSerializer,
    TicketApproveSerializer, TicketStatusSerializer, SignTaskSerializer,
)

__all__ = [
    'ServiceCategorySerializer', 'ServiceCategoryCreateUpdateSerializer',
    'SlaPolicySerializer',
    'IncidentSerializer', 'IncidentCreateUpdateSerializer',
    'ChangeSerializer', 'ChangeCreateUpdateSerializer',
    'ServiceRequestSerializer',
    'ProblemSerializer', 'ProblemCreateUpdateSerializer',
    'WorkflowSerializer', 'WorkflowCreateSerializer', 'WorkflowVersionSerializer',
    'StateSerializer', 'TransitionSerializer', 'FieldSerializer',
    'TicketSerializer', 'TicketCreateSerializer', 'TicketSubmitSerializer',
    'TicketApproveSerializer', 'TicketStatusSerializer', 'SignTaskSerializer',
]
