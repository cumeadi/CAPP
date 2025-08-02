"""
USSD Protocol Handler for Mobile Money

Handles USSD-based mobile money operations including menu navigation,
transaction processing, and user interactions.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import structlog

from pydantic import BaseModel, Field

from ..base_mmo import MMOTransaction, TransactionStatus, TransactionType

logger = structlog.get_logger(__name__)


class USSDMenuType(str, Enum):
    """USSD menu types"""
    MAIN_MENU = "main_menu"
    PAYMENT_MENU = "payment_menu"
    AMOUNT_ENTRY = "amount_entry"
    PHONE_ENTRY = "phone_entry"
    CONFIRMATION = "confirmation"
    SUCCESS = "success"
    ERROR = "error"


class USSDMenuOption(BaseModel):
    """USSD menu option"""
    option_number: str
    option_text: str
    next_menu: Optional[str] = None
    action: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class USSDMenu(BaseModel):
    """USSD menu definition"""
    menu_id: str
    menu_type: USSDMenuType
    title: str
    message: str
    options: List[USSDMenuOption] = Field(default_factory=list)
    input_required: bool = False
    input_type: Optional[str] = None  # "amount", "phone", "text"
    validation_regex: Optional[str] = None
    max_length: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class USSDRequest(BaseModel):
    """USSD request model"""
    session_id: str
    phone_number: str
    service_code: str
    text: str
    network_code: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class USSDResponse(BaseModel):
    """USSD response model"""
    session_id: str
    message: str
    end_session: bool = False
    next_menu: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class USSDTransaction(BaseModel):
    """USSD transaction model"""
    session_id: str
    transaction_id: str
    amount: Decimal
    phone_number: str
    description: str
    status: TransactionStatus = TransactionStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class USSDConfig(BaseModel):
    """USSD configuration"""
    service_code: str = "*123#"
    max_session_duration: int = 300  # 5 minutes
    max_menu_depth: int = 5
    enable_timeout: bool = True
    timeout_seconds: int = 60
    enable_session_persistence: bool = True
    session_storage_ttl: int = 3600  # 1 hour
    metadata: Dict[str, Any] = Field(default_factory=dict)


class USSDProtocolHandler:
    """
    USSD Protocol Handler
    
    Handles USSD-based mobile money operations with:
    - Menu navigation and state management
    - Input validation and processing
    - Transaction initiation and tracking
    - Session management and timeout handling
    """
    
    def __init__(self, config: USSDConfig):
        self.config = config
        self.logger = structlog.get_logger(__name__)
        
        # Session management
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.menu_definitions: Dict[str, USSDMenu] = {}
        
        # Initialize menus
        self._initialize_menus()
    
    def _initialize_menus(self) -> None:
        """Initialize USSD menu definitions"""
        try:
            # Main menu
            main_menu = USSDMenu(
                menu_id="main_menu",
                menu_type=USSDMenuType.MAIN_MENU,
                title="CAPP Mobile Money",
                message="Welcome to CAPP Mobile Money\n\n1. Send Money\n2. Check Balance\n3. Transaction History\n4. Help\n0. Exit",
                options=[
                    USSDMenuOption(
                        option_number="1",
                        option_text="Send Money",
                        next_menu="payment_menu"
                    ),
                    USSDMenuOption(
                        option_number="2",
                        option_text="Check Balance",
                        action="check_balance"
                    ),
                    USSDMenuOption(
                        option_number="3",
                        option_text="Transaction History",
                        action="transaction_history"
                    ),
                    USSDMenuOption(
                        option_number="4",
                        option_text="Help",
                        action="help"
                    ),
                    USSDMenuOption(
                        option_number="0",
                        option_text="Exit",
                        action="exit"
                    )
                ]
            )
            
            # Payment menu
            payment_menu = USSDMenu(
                menu_id="payment_menu",
                menu_type=USSDMenuType.PAYMENT_MENU,
                title="Send Money",
                message="Enter recipient phone number:",
                input_required=True,
                input_type="phone",
                validation_regex=r"^\+?[1-9]\d{1,14}$",
                max_length=15
            )
            
            # Amount entry menu
            amount_menu = USSDMenu(
                menu_id="amount_entry",
                menu_type=USSDMenuType.AMOUNT_ENTRY,
                title="Enter Amount",
                message="Enter amount to send:",
                input_required=True,
                input_type="amount",
                validation_regex=r"^\d+(\.\d{1,2})?$",
                max_length=10
            )
            
            # Confirmation menu
            confirmation_menu = USSDMenu(
                menu_id="confirmation",
                menu_type=USSDMenuType.CONFIRMATION,
                title="Confirm Transaction",
                message="Please confirm your transaction:\n\nRecipient: {phone_number}\nAmount: {amount}\nFee: {fee}\nTotal: {total}\n\n1. Confirm\n2. Cancel",
                options=[
                    USSDMenuOption(
                        option_number="1",
                        option_text="Confirm",
                        action="confirm_transaction"
                    ),
                    USSDMenuOption(
                        option_number="2",
                        option_text="Cancel",
                        action="cancel_transaction"
                    )
                ]
            )
            
            # Success menu
            success_menu = USSDMenu(
                menu_id="success",
                menu_type=USSDMenuType.SUCCESS,
                title="Transaction Successful",
                message="Your transaction was successful!\n\nTransaction ID: {transaction_id}\nAmount: {amount}\nRecipient: {phone_number}\n\nThank you for using CAPP Mobile Money.",
                end_session=True
            )
            
            # Error menu
            error_menu = USSDMenu(
                menu_id="error",
                menu_type=USSDMenuType.ERROR,
                title="Transaction Failed",
                message="Your transaction failed.\n\nError: {error_message}\n\nPlease try again or contact support.",
                options=[
                    USSDMenuOption(
                        option_number="1",
                        option_text="Try Again",
                        next_menu="main_menu"
                    ),
                    USSDMenuOption(
                        option_number="0",
                        option_text="Exit",
                        action="exit"
                    )
                ]
            )
            
            # Store menu definitions
            self.menu_definitions = {
                "main_menu": main_menu,
                "payment_menu": payment_menu,
                "amount_entry": amount_menu,
                "confirmation": confirmation_menu,
                "success": success_menu,
                "error": error_menu
            }
            
            self.logger.info("USSD menus initialized")
            
        except Exception as e:
            self.logger.error("Failed to initialize USSD menus", error=str(e))
            raise
    
    async def process_request(self, request: USSDRequest) -> USSDResponse:
        """
        Process USSD request and return appropriate response
        
        Args:
            request: USSD request from user
            
        Returns:
            USSDResponse: Response to send to user
        """
        try:
            # Validate session
            session = await self._get_or_create_session(request.session_id, request.phone_number)
            
            # Update session with current request
            session["last_activity"] = datetime.now(timezone.utc)
            session["current_request"] = request
            
            # Process user input
            if not request.text:
                # First request - show main menu
                return await self._show_menu("main_menu", session)
            else:
                # Process user selection/input
                return await self._process_user_input(request, session)
                
        except Exception as e:
            self.logger.error("Failed to process USSD request", error=str(e))
            
            return USSDResponse(
                session_id=request.session_id,
                message="An error occurred. Please try again.",
                end_session=True
            )
    
    async def _get_or_create_session(self, session_id: str, phone_number: str) -> Dict[str, Any]:
        """Get or create a new USSD session"""
        try:
            if session_id in self.active_sessions:
                session = self.active_sessions[session_id]
                
                # Check if session has expired
                if self.config.enable_timeout:
                    last_activity = session.get("last_activity")
                    if last_activity and (datetime.now(timezone.utc) - last_activity).total_seconds() > self.config.timeout_seconds:
                        # Session expired, remove it
                        del self.active_sessions[session_id]
                    else:
                        return session
            
            # Create new session
            session = {
                "session_id": session_id,
                "phone_number": phone_number,
                "created_at": datetime.now(timezone.utc),
                "last_activity": datetime.now(timezone.utc),
                "current_menu": "main_menu",
                "menu_stack": ["main_menu"],
                "transaction_data": {},
                "metadata": {}
            }
            
            self.active_sessions[session_id] = session
            
            self.logger.info("Created new USSD session", session_id=session_id, phone_number=phone_number)
            
            return session
            
        except Exception as e:
            self.logger.error("Failed to get or create session", error=str(e))
            raise
    
    async def _show_menu(self, menu_id: str, session: Dict[str, Any]) -> USSDResponse:
        """Show a specific menu to the user"""
        try:
            menu = self.menu_definitions.get(menu_id)
            if not menu:
                return USSDResponse(
                    session_id=session["session_id"],
                    message="Menu not found. Please try again.",
                    end_session=True
                )
            
            # Update session
            session["current_menu"] = menu_id
            
            # Format menu message with dynamic content
            message = await self._format_menu_message(menu, session)
            
            return USSDResponse(
                session_id=session["session_id"],
                message=message,
                next_menu=menu_id,
                metadata={"menu_type": menu.menu_type.value}
            )
            
        except Exception as e:
            self.logger.error("Failed to show menu", error=str(e))
            raise
    
    async def _format_menu_message(self, menu: USSDMenu, session: Dict[str, Any]) -> str:
        """Format menu message with dynamic content"""
        try:
            message = menu.message
            
            # Replace placeholders with actual values
            transaction_data = session.get("transaction_data", {})
            
            placeholders = {
                "{phone_number}": transaction_data.get("recipient_phone", ""),
                "{amount}": str(transaction_data.get("amount", "")),
                "{fee}": str(transaction_data.get("fee", "0.00")),
                "{total}": str(transaction_data.get("total", "")),
                "{transaction_id}": transaction_data.get("transaction_id", ""),
                "{error_message}": transaction_data.get("error_message", "Unknown error")
            }
            
            for placeholder, value in placeholders.items():
                message = message.replace(placeholder, value)
            
            return message
            
        except Exception as e:
            self.logger.error("Failed to format menu message", error=str(e))
            return menu.message
    
    async def _process_user_input(self, request: USSDRequest, session: Dict[str, Any]) -> USSDResponse:
        """Process user input and determine next action"""
        try:
            current_menu = self.menu_definitions.get(session["current_menu"])
            if not current_menu:
                return USSDResponse(
                    session_id=session["session_id"],
                    message="Invalid menu state. Please try again.",
                    end_session=True
                )
            
            # Handle input based on menu type
            if current_menu.input_required:
                # Process user input
                return await self._process_menu_input(request, current_menu, session)
            else:
                # Process menu option selection
                return await self._process_menu_selection(request, current_menu, session)
                
        except Exception as e:
            self.logger.error("Failed to process user input", error=str(e))
            raise
    
    async def _process_menu_input(self, request: USSDRequest, menu: USSDMenu, session: Dict[str, Any]) -> USSDResponse:
        """Process input for menus that require user input"""
        try:
            user_input = request.text.strip()
            
            # Validate input
            if not await self._validate_input(user_input, menu):
                return USSDResponse(
                    session_id=session["session_id"],
                    message=f"Invalid input. Please enter a valid {menu.input_type}.",
                    next_menu=session["current_menu"]
                )
            
            # Store input in session
            if menu.input_type == "phone":
                session["transaction_data"]["recipient_phone"] = user_input
                # Move to amount entry
                return await self._show_menu("amount_entry", session)
            elif menu.input_type == "amount":
                amount = Decimal(user_input)
                session["transaction_data"]["amount"] = amount
                session["transaction_data"]["fee"] = self._calculate_fee(amount)
                session["transaction_data"]["total"] = amount + session["transaction_data"]["fee"]
                # Move to confirmation
                return await self._show_menu("confirmation", session)
            
            return USSDResponse(
                session_id=session["session_id"],
                message="Invalid input type.",
                end_session=True
            )
            
        except Exception as e:
            self.logger.error("Failed to process menu input", error=str(e))
            raise
    
    async def _process_menu_selection(self, request: USSDRequest, menu: USSDMenu, session: Dict[str, Any]) -> USSDResponse:
        """Process menu option selection"""
        try:
            user_selection = request.text.strip()
            
            # Find selected option
            selected_option = None
            for option in menu.options:
                if option.option_number == user_selection:
                    selected_option = option
                    break
            
            if not selected_option:
                return USSDResponse(
                    session_id=session["session_id"],
                    message="Invalid selection. Please try again.",
                    next_menu=session["current_menu"]
                )
            
            # Handle option action
            if selected_option.action:
                return await self._handle_menu_action(selected_option.action, session)
            elif selected_option.next_menu:
                return await self._show_menu(selected_option.next_menu, session)
            else:
                return USSDResponse(
                    session_id=session["session_id"],
                    message="Invalid menu option.",
                    end_session=True
                )
                
        except Exception as e:
            self.logger.error("Failed to process menu selection", error=str(e))
            raise
    
    async def _handle_menu_action(self, action: str, session: Dict[str, Any]) -> USSDResponse:
        """Handle menu action"""
        try:
            if action == "check_balance":
                return await self._handle_check_balance(session)
            elif action == "transaction_history":
                return await self._handle_transaction_history(session)
            elif action == "help":
                return await self._handle_help(session)
            elif action == "confirm_transaction":
                return await self._handle_confirm_transaction(session)
            elif action == "cancel_transaction":
                return await self._handle_cancel_transaction(session)
            elif action == "exit":
                return USSDResponse(
                    session_id=session["session_id"],
                    message="Thank you for using CAPP Mobile Money. Goodbye!",
                    end_session=True
                )
            else:
                return USSDResponse(
                    session_id=session["session_id"],
                    message="Invalid action.",
                    end_session=True
                )
                
        except Exception as e:
            self.logger.error("Failed to handle menu action", error=str(e))
            raise
    
    async def _handle_check_balance(self, session: Dict[str, Any]) -> USSDResponse:
        """Handle balance check action"""
        try:
            # This would integrate with the actual mobile money provider
            # For now, return a mock balance
            balance = "1,250.00"
            
            message = f"Your current balance is: KES {balance}\n\n1. Back to Main Menu\n0. Exit"
            
            return USSDResponse(
                session_id=session["session_id"],
                message=message,
                metadata={"action": "check_balance", "balance": balance}
            )
            
        except Exception as e:
            self.logger.error("Failed to handle check balance", error=str(e))
            raise
    
    async def _handle_transaction_history(self, session: Dict[str, Any]) -> USSDResponse:
        """Handle transaction history action"""
        try:
            # This would integrate with the actual mobile money provider
            # For now, return mock history
            message = "Recent Transactions:\n\n1. Sent KES 500 to +254700123456\n2. Received KES 1,000 from +254700789012\n3. Sent KES 250 to +254700345678\n\n1. Back to Main Menu\n0. Exit"
            
            return USSDResponse(
                session_id=session["session_id"],
                message=message,
                metadata={"action": "transaction_history"}
            )
            
        except Exception as e:
            self.logger.error("Failed to handle transaction history", error=str(e))
            raise
    
    async def _handle_help(self, session: Dict[str, Any]) -> USSDResponse:
        """Handle help action"""
        try:
            message = "CAPP Mobile Money Help:\n\nFor support, call: +254700000000\nEmail: support@capp.com\n\n1. Back to Main Menu\n0. Exit"
            
            return USSDResponse(
                session_id=session["session_id"],
                message=message,
                metadata={"action": "help"}
            )
            
        except Exception as e:
            self.logger.error("Failed to handle help", error=str(e))
            raise
    
    async def _handle_confirm_transaction(self, session: Dict[str, Any]) -> USSDResponse:
        """Handle transaction confirmation"""
        try:
            transaction_data = session.get("transaction_data", {})
            
            # Create USSD transaction
            ussd_transaction = USSDTransaction(
                session_id=session["session_id"],
                transaction_id=f"USSD_{session['session_id']}_{int(datetime.now(timezone.utc).timestamp())}",
                amount=transaction_data.get("amount", Decimal("0")),
                phone_number=transaction_data.get("recipient_phone", ""),
                description="USSD Money Transfer"
            )
            
            # This would integrate with the actual mobile money provider
            # For now, simulate successful transaction
            ussd_transaction.status = TransactionStatus.SUCCESSFUL
            ussd_transaction.completed_at = datetime.now(timezone.utc)
            
            # Store transaction in session
            session["transaction_data"]["transaction_id"] = ussd_transaction.transaction_id
            
            # Show success menu
            return await self._show_menu("success", session)
            
        except Exception as e:
            self.logger.error("Failed to handle confirm transaction", error=str(e))
            
            # Show error menu
            session["transaction_data"]["error_message"] = str(e)
            return await self._show_menu("error", session)
    
    async def _handle_cancel_transaction(self, session: Dict[str, Any]) -> USSDResponse:
        """Handle transaction cancellation"""
        try:
            # Clear transaction data
            session["transaction_data"] = {}
            
            # Return to main menu
            return await self._show_menu("main_menu", session)
            
        except Exception as e:
            self.logger.error("Failed to handle cancel transaction", error=str(e))
            raise
    
    async def _validate_input(self, user_input: str, menu: USSDMenu) -> bool:
        """Validate user input based on menu requirements"""
        try:
            if not user_input:
                return False
            
            # Check length
            if menu.max_length and len(user_input) > menu.max_length:
                return False
            
            # Check regex pattern
            if menu.validation_regex:
                import re
                if not re.match(menu.validation_regex, user_input):
                    return False
            
            # Type-specific validation
            if menu.input_type == "amount":
                try:
                    amount = Decimal(user_input)
                    if amount <= 0:
                        return False
                except:
                    return False
            elif menu.input_type == "phone":
                # Basic phone number validation
                clean_number = ''.join(filter(str.isdigit, user_input))
                if len(clean_number) < 9 or len(clean_number) > 15:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to validate input", error=str(e))
            return False
    
    def _calculate_fee(self, amount: Decimal) -> Decimal:
        """Calculate transaction fee"""
        try:
            # Simple fee calculation
            if amount <= Decimal("100"):
                return Decimal("10")
            elif amount <= Decimal("1000"):
                return Decimal("25")
            else:
                return Decimal("50")
                
        except Exception as e:
            self.logger.error("Failed to calculate fee", error=str(e))
            return Decimal("0")
    
    async def cleanup_expired_sessions(self) -> None:
        """Clean up expired sessions"""
        try:
            current_time = datetime.now(timezone.utc)
            expired_sessions = []
            
            for session_id, session in self.active_sessions.items():
                last_activity = session.get("last_activity")
                if last_activity and (current_time - last_activity).total_seconds() > self.config.max_session_duration:
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                del self.active_sessions[session_id]
            
            if expired_sessions:
                self.logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
                
        except Exception as e:
            self.logger.error("Failed to cleanup expired sessions", error=str(e))
    
    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific session"""
        return self.active_sessions.get(session_id)
    
    async def get_active_sessions_count(self) -> int:
        """Get count of active sessions"""
        return len(self.active_sessions)
    
    async def close(self) -> None:
        """Close USSD protocol handler"""
        try:
            # Clear all sessions
            self.active_sessions.clear()
            
            self.logger.info("USSD protocol handler closed")
            
        except Exception as e:
            self.logger.error("Error closing USSD protocol handler", error=str(e)) 