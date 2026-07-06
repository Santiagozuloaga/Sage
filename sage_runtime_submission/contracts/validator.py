"""
SAGE OS Contract Validator

Contract validation and RFC policy enforcement.
"""

import logging
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from .models import Contract, ContractStatus, RFC


logger = logging.getLogger(__name__)


class ContractValidator:
    """
    Contract Validator for SAGE OS.
    
    Validates contracts, enforces RFC policies,
    and manages PR workflow compliance.
    """

    def __init__(self):
        self._contracts: Dict[str, Contract] = {}
        self._rfcs: Dict[str, RFC] = {}
        self._initialized = False

    async def initialize(self):
        """Initialize the validator."""
        self._initialized = True
        logger.info("[CONTRACT_VALIDATOR] Initialized")

    async def create_contract(
        self,
        title: str,
        description: str,
        content: Dict[str, Any],
        author: str
    ) -> Contract:
        """Create a new contract."""
        contract = Contract(
            contract_id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            status=ContractStatus.DRAFT,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            author=author,
            reviewers=[],
            content=content
        )
        self._contracts[contract.contract_id] = contract
        logger.info(f"[CONTRACT_VALIDATOR] Created contract: {contract.contract_id}")
        return contract

    async def validate_contract(self, contract_id: str) -> bool:
        """Validate a contract against policies."""
        if contract_id not in self._contracts:
            logger.error(f"[CONTRACT_VALIDATOR] Contract not found: {contract_id}")
            return False
        
        contract = self._contracts[contract_id]
        
        # Basic validation rules
        if not contract.title:
            logger.error(f"[CONTRACT_VALIDATOR] Contract missing title: {contract_id}")
            return False
        
        if not contract.content:
            logger.error(f"[CONTRACT_VALIDATOR] Contract missing content: {contract_id}")
            return False
        
        logger.info(f"[CONTRACT_VALIDATOR] Contract validated: {contract_id}")
        return True

    async def approve_contract(self, contract_id: str, reviewer: str) -> bool:
        """Approve a contract."""
        if contract_id not in self._contracts:
            return False
        
        contract = self._contracts[contract_id]
        if reviewer not in contract.reviewers:
            contract.reviewers.append(reviewer)
        
        contract.status = ContractStatus.APPROVED
        contract.updated_at = datetime.now()
        
        logger.info(f"[CONTRACT_VALIDATOR] Contract approved: {contract_id} by {reviewer}")
        return True

    async def create_rfc(
        self,
        title: str,
        description: str,
        author: str
    ) -> RFC:
        """Create a new RFC."""
        rfc = RFC(
            rfc_id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            status="draft",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            author=author,
            discussion=[]
        )
        self._rfcs[rfc.rfc_id] = rfc
        logger.info(f"[CONTRACT_VALIDATOR] Created RFC: {rfc.rfc_id}")
        return rfc

    async def submit_rfc(self, rfc_id: str) -> bool:
        """Submit an RFC for review."""
        if rfc_id not in self._rfcs:
            return False
        
        rfc = self._rfcs[rfc_id]
        rfc.status = "submitted"
        rfc.updated_at = datetime.now()
        
        logger.info(f"[CONTRACT_VALIDATOR] RFC submitted: {rfc_id}")
        return True

    def get_contract(self, contract_id: str) -> Optional[Contract]:
        """Get a contract by ID."""
        return self._contracts.get(contract_id)

    def get_rfc(self, rfc_id: str) -> Optional[RFC]:
        """Get an RFC by ID."""
        return self._rfcs.get(rfc_id)

    def list_contracts(self, status: Optional[ContractStatus] = None) -> List[Contract]:
        """List contracts, optionally filtered by status."""
        contracts = list(self._contracts.values())
        if status:
            contracts = [c for c in contracts if c.status == status]
        return contracts

    def list_rfcs(self) -> List[RFC]:
        """List all RFCs."""
        return list(self._rfcs.values())

    async def shutdown(self):
        """Shutdown the validator."""
        self._initialized = False
        logger.info("[CONTRACT_VALIDATOR] Shutdown complete")
