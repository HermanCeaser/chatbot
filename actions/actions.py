

# This is a simple example for a custom action which utters "Hello World!"

# from typing import Any, Text, Dict, List
#
# from rasa_sdk import Action, Tracker
# from rasa_sdk.executor import CollectingDispatcher
#
#
# class ActionHelloWorld(Action):
#
#     def name(self) -> Text:
#         return "action_hello_world"
#
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#
#         dispatcher.utter_message(text="Hello World!")
#
#         return []

"""Custom actions"""
import json
import random
import re
import datetime
from typing import Dict, Text, Any, List, Optional
import logging
from rasa_sdk.interfaces import Action
from rasa_sdk.events import (
    SlotSet,
    AllSlotsReset,
    EventType,
    ActionExecuted,
    SessionStarted,
    Restarted,
    FollowupAction,
    UserUtteranceReverted,
    ActionExecutionRejected
)
from rasa_sdk import Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from rasa_sdk.types import DomainDict


logger = logging.getLogger(__name__)

MOCK_DATA = json.load(open("actions/mock_data.json", "r"))
NEW_POLICIES = json.load(open("actions/new_policies.json", "r"))
DOB_PATTERN = "^([0-2][0-9]|(3)[0-1])(\/)(((0)[0-9])|((1)[0-2]))(\/)\d{4}$"

US_STATES = ["AZ", "AL", "AK", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY",
             "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH",
             "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"]


# Get New Quote Actions
class ValidateGetFirstname(FormValidationAction):

    def name(self):
        return "validate_get_firstname"

    def validate_firstname(self, value: Text, dispatcher: CollectingDispatcher, tracker: Tracker,  domain: Dict[Text, Any]):
        if tracker.get_intent_of_latest_message() == "buy_insurance":
            return {"firstname": None}

        firstname = tracker.get_slot("firstname")

        if isinstance(firstname, str):
            firstname = firstname.split()[0]
        else:
            dispatcher.utter_message("First name should be a string")
            return {"firstname": None}
        return {"firstname": firstname}


class ActionGetFirstname(Action):
    def name(self):
        return "action_get_firstname"

    async def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]):
        slots = ["firstname"]

        firstname = tracker.get_slot("firstname")

        if firstname is not None:
            dispatcher.utter_message(
                response="utter_greet", firstname=firstname)

        return [SlotSet(slot, None) for slot in slots]


class ActionGetQuote(Action):
    """Gets an insurance quote"""

    def name(self) -> Text:
        """Unique identifier for the action."""
        return "action_get_quote"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Executes the action"""
        slots = ["AA_quote_insurance_type", "quote_state",
                 "quote_number_persons", "number", "state"]

        # Build the quote from the provided data.
        insurance_type = tracker.get_slot("AA_quote_insurance_type")
        n_persons = int(tracker.get_slot("quote_number_persons"))

        baseline_rate = MOCK_DATA["policy_quote"]["insurance_type"][insurance_type]
        final_quote = baseline_rate * n_persons

        msg_params = {
            "final_quote": final_quote,
            "insurance_type": insurance_type.capitalize(),
            "quote_state": tracker.get_slot("quote_state"),
            "n_persons": n_persons
        }
        dispatcher.utter_message(response="utter_final_quote", **msg_params)

        # Reset the slot values.
        return [SlotSet(slot, None) for slot in slots]


class ValidateQuoteForm(FormValidationAction):
    """Validates Slots for the Quote form."""

    def name(self) -> Text:
        """Unique identifier for the action."""
        return "validate_quote_form"

    def validate_AA_quote_insurance_type(
            self,
            value: Text,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Validates value of 'amount-of-money' slot"""
        insurance_type = value

        if insurance_type.lower() not in ["auto", "health", "life", "home"]:
            dispatcher.utter_message("Must select a valid type of insurance")
            return {"AA_quote_insurance_type": None}

        return {"AA_quote_insurance_type": insurance_type}

    def validate_quote_state(
            self,
            value: Text,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Validates the state provided by user to get an insurance quote."""
        state_entity = next(tracker.get_latest_entity_values("state"), None)

        if state_entity not in US_STATES:
            dispatcher.utter_message(
                f"{state_entity} is invalid. Please provide a valid state.")
            return {"quote_state": None}

        return {"quote_state": state_entity}

    def validate_quote_number_persons(
            self,
            value: Text,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:
        """Validates the number of persons entered is valid."""
        if tracker.get_intent_of_latest_message() == "stop":
            return {"quote_number_persons": None}

        try:
            int(value)
        except TypeError:
            dispatcher.utter_message(f"Number of persons must be a number.")
            return {"quote_number_persons": None}
        except ValueError:
            dispatcher.utter_message("You must answer with a number.")
            return {"quote_number_persons": None}

        if int(value) <= 0:
            dispatcher.utter_message(
                "Number of people on policy must be >= 1.")
            return {"quote_number_persons": None}

        return {"quote_number_persons": value}


class ActionStopQuote(Action):
    """Stops quote form and clears collected data."""

    def name(self) -> Text:
        """Unique identifier for the action."""
        return "action_stop_quote"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Executes the action"""
        slots = ["AA_quote_insurance_type",
                 "quote_state", "quote_number_persons"]

        # Reset the slot values.
        return [SlotSet(slot, None) for slot in slots]


class ActionCheckClaimBalance(Action):
    """Preps user to browse recent claims."""

    def name(self) -> Text:
        return "action_check_claim_balance"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[EventType]:
        active_claim = tracker.get_slot("claim_id")

        clm = next((c for c in MOCK_DATA["claims"] if str(
            c["claim_id"]) == active_claim), None)

        has_outstanding_balance = clm["claim_balance"] > 0

        print("Outstanding balance", has_outstanding_balance)

        return [SlotSet("has_outstanding_balance", has_outstanding_balance)]

# Buy Insurance Actions


class ValidateBuyInsuranceForm(FormValidationAction):
    """ Validates slots for buy insurance form """

    def name(self) -> Text:
        """ unique identifier for the action """
        return "validate_buy_insurance_form"

    async def validate_insurance_policy_type(
            self,
            value: Text,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Validates value of 'insurance-provider' slot"""
        if tracker.get_intent_of_latest_message() == "get_a_quote":
            return {"insurance_policy_type": None}

        insurance_policy_type = tracker.get_slot("insurance_policy_type")

        if isinstance(insurance_policy_type, list):
            insurance_policy_type = next(
                tracker.get_latest_entity_values("quote_insurance_type"), None)
            # insurance_policy_type = insurance_policy_type[0]

        print(value, insurance_policy_type)

        if insurance_policy_type.lower() not in ["auto", "health", "life", "home"]:
            dispatcher.utter_message(
                "Must select a valid type of insurance type")
            return {"insurance_policy_type": None}

        return {"insurance_policy_type": insurance_policy_type}

    async def validate_insurance_provider(
            self,
            value: Text,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Validates value of 'insurance-provider' slot"""
        insurance_provider = value
        print(value)

        if insurance_provider.lower() not in ["jubilee", "uap", "icea", "swico", "prudential", "britam"]:
            dispatcher.utter_message("Must select a valid type of insurance")
            return {"insurance_provider": None}

        return {"insurance_provider": insurance_provider}

    async def validate_number_of_persons(
            self,
            value: Text,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:
        """Validates the number of persons entered is valid."""
        print(value)
        if tracker.get_intent_of_latest_message() == "stop":
            return {"number_of_persons": None}

        if tracker.get_intent_of_latest_message() == "get_a_quote":
            return {"number_of_persons": None}

        n_persons = tracker.get_slot("number_of_persons")

        if isinstance(n_persons, list):
            n_persons = n_persons[0].split()[0]
        else:
            n_persons = n_persons.split()[0]

        try:
            int(n_persons)
        except TypeError:
            dispatcher.utter_message(f"Number of persons must be a number.")
            return {"number_of_persons": None}
        except ValueError:
            dispatcher.utter_message("You must answer with a number.")
            return {"number_of_persons": None}

        print(f"number of persons: {n_persons}")

        if int(n_persons) <= 0:
            dispatcher.utter_message(
                "Number of people on policy must be >= 1.")
            return {"number_of_persons": None}

        return {"quote_number_persons": n_persons}

    async def validate_fullname(
            self,
            value: Text,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Validates value of 'insurance-provider' slot"""
        print(value)
        if tracker.get_intent_of_latest_message() == 'stop':
            return {"fullname": None}
        fullname = value

        if fullname is None or len(fullname) == 0:
            dispatcher.utter_message("Name cannot be empty")
            return {"fullname": None}

        return {"fullname": fullname}

    async def validate_dob(self, value: Text, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any],) -> Dict[Text, Any]:
        """Validates value of 'dob' slot"""

        # check whether entered date is a valid dob
        dob = tracker.get_slot("dob")

        # Sometimes slot is being double filled.
        if isinstance(dob, list):
            dob = next(tracker.get_latest_entity_values("dob"), None)
        print(value, dob)

        # Check if date matches required pattern
        if bool(re.match(DOB_PATTERN, str(dob))):
            return {"dob": dob}
        else:
            dispatcher.utter_message(
                f"{dob}, is not in the required format, enter date as 'dd/mm/yyy' ")
            return {"dob": None}

    async def validate_coverage(
            self,
            value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:
        """Validates whether the annual income entered is valid."""

        if tracker.get_intent_of_latest_message() == "get_a_quote":
            return {"coverage": None}

        print(f"coverage {value}")
        try:
            float(value)
        except TypeError:
            dispatcher.utter_message(f"Coverage should be a number.")
            return {"coverage": None}
        except ValueError:
            dispatcher.utter_message("You must answer with a number.")
            return {"coverage": None}

        if float(value) not in [40000.0, 70000.0, 100000.0]:
            dispatcher.utter_message(
                "Enter an appropriate coverage as shown in the above list")
            return {"coverage": None}

        return {"coverage": value}

    async def validate_gender(self, value: Text, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any],) -> Dict[Text, Any]:
        """Validates the 'gender' slot value"""
        if value.lower() not in ["male", "female"]:
            dispatcher.utter_message("Must Select a valid gender type")
            return {"gender": None}
        return {"gender": value}

    async def validate_policy_duration(self, value: Text, dispatcher: CollectingDispatcher, tracker: Tracker, domain):
        """Validates the number of years of Policy duration."""
        if tracker.get_intent_of_latest_message() == "get_a_quote":
            return {"policy_duration": None}

        duration = tracker.get_slot('policy_duration')
        if duration is None:
            dispatcher.utter_message(f"Policy duration needs to be a number.")
            return {"policy_duration": None}

        if isinstance(duration, str):
            duration = duration.split()[0]

        print(f"policy duraion: ({value}, {duration})")

        try:
            int(duration)
        except TypeError:
            dispatcher.utter_message(f"The policy duration must be a number.")
            return {"policy_duration": None}
        except ValueError:
            dispatcher.utter_message("You must answer with a number of years.")
            return {"policy_duration": None}

        if int(duration) not in [3, 5, 10]:
            dispatcher.utter_message(
                "policy_duration  must be  either  3, 5, or 10 years. Try again")
            return {"policy_duration": None}

        return {"policy_duration": duration}

    async def validate_annual_income(
            self,
            value: Text,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:
        """Validates whether the annual income entered is valid."""
        if tracker.get_intent_of_latest_message() == "get_a_quote":
            return {"annual_income": None}

        print(f"annual income: {value}")
        try:
            float(value)
        except TypeError:
            dispatcher.utter_message(
                f"Annual income aerned should be a number.")
            return {"annual_income": None}
        except ValueError:
            dispatcher.utter_message("You must answer with a number.")
            return {"annual_income": None}

        if float(value) <= 10.0:
            dispatcher.utter_message(
                "Annual income must be greater than 10")
            return {"annual_income": None}

        return {"annual_income": value}


class ActionBuyInsurance(Action):
    """ Buy an Insurance Policy for a person """

    def name(self):
        return "action_buy_insurance"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:

        slots = ["insurance_provider", "insurance_policy_type", "fullname",
                 "dob", "gender", "number_of_persons", "coverage", "annual_income", "policy_duration"]

        # Buy the policy from provided data
        insurance_provider = tracker.get_slot("insurance_provider")
        policy = tracker.get_slot("insurance_policy_type")
        policy_duration = tracker.get_slot("policy_duration")
        n_persons = tracker.get_slot("number_of_persons")
        policy_holder = tracker.get_slot("fullname")
        sum_assured = tracker.get_slot("coverage")

        if policy_duration is None:
            policy_duration = 3

        if insurance_provider is not None:
            baseline_rate = MOCK_DATA["policy_quote"]["insurance_type"][policy]
            final_rate = baseline_rate * int(policy_duration) * int(n_persons)

            msg_params = {
                "final_rate": final_rate,
                "final_rate_quarterly": final_rate * 4,
                "final_rate_annually": final_rate * 12,
                "first_name": policy_holder.split()[0].capitalize(),
                "insurance_type": policy.capitalize(),
                "insurance_provider": insurance_provider.capitalize(),
                "policy_holder": policy_holder,
                "sum_assured": sum_assured,
                "policy_duration": policy_duration,
                "n_persons": n_persons
            }
            dispatcher.utter_message(
                response="utter_buy_insurance", **msg_params)
        else:
            dispatcher.utter_message(
                "The selected Insurance policy is not provided by the provider")

        return AllSlotsReset()


# Change Address Actions


class AskConfirmAddress(Action):
    """Retrieves existing user address and asks for the user to verify the address."""

    def name(self) -> Text:
        return "action_ask_verify_address"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[EventType]:
        # Load the member address from the JSON document.
        address_slots = {
            "address_street": MOCK_DATA["member_info"]["home_address"]["address_street"],
            "address_city": MOCK_DATA["member_info"]["home_address"]["address_city"],
            "address_state": MOCK_DATA["member_info"]["home_address"]["address_state"],
            "address_zip": MOCK_DATA["member_info"]["home_address"]["address_zip"]
        }

        # Build the full address.
        address_line_two = f"{address_slots['address_city']}, {address_slots['address_state']} " \
                           f"{address_slots['address_zip']}"
        full_address = "\n".join(
            [address_slots['address_street'], address_line_two])
        address_slots["full_address"] = full_address

        dispatcher.utter_message(
            response="utter_confirm_address", **address_slots)

        return [SlotSet(k, v) for k, v in address_slots.items()]


class ActionVerifyAddress(Action):
    """Checks if the user confirms their address or not."""

    def name(self) -> Text:
        return "action_verify_address_form"

    def run(
        self, dispather: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[EventType]:
        address_slots = ["address_street",
                         "address_city",
                         "address_state",
                         "address_zip"]

        verify_address = tracker.get_slot("verify_address")

        # Reset the address slots if user doesn't verify address so the change address form can collect new address.
        if not verify_address:
            return [SlotSet(a, None) for a in address_slots]

        return [SlotSet("verify_address", verify_address)]


class ActionResetAddress(Action):
    """Checks if the user confirms their address or not."""

    def name(self) -> Text:
        return "action_reset_address"

    def run(
        self, dispather: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[EventType]:
        address_slots = ["address_street",
                         "address_city",
                         "address_state",
                         "address_zip",
                         "full_address"]

        return [SlotSet(a, None) for a in address_slots]


class ValidateVerifyAddressForm(FormValidationAction):

    def name(self) -> Text:
        return "validate_verify_address_form"

    async def validate_verify_address(
            self,
            value: Text,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        verify_address = tracker.get_slot("verify_address")

        return {"verify_address": verify_address}


class ActionGetAddress(Action):

    def name(self) -> Text:
        return "action_get_address"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[EventType]:
        address_slots = {
            "address_street": MOCK_DATA["member_info"]["home_address"]["address_street"],
            "address_city": MOCK_DATA["member_info"]["home_address"]["address_city"],
            "address_state": MOCK_DATA["member_info"]["home_address"]["address_state"],
            "address_zip": MOCK_DATA["member_info"]["home_address"]["address_zip"]
        }

        # Build the full address.
        address_line_two = f"{address_slots['address_city']}, {address_slots['address_state']} " \
                           f"{address_slots['address_zip']}"
        full_address = "\n".join(
            [address_slots['address_street'], address_line_two])
        address_slots["full_address"] = full_address

        dispatcher.utter_message(
            text=f"The address we have on file is:\n{full_address}")

        return []


class ActionUpdateAddress(Action):

    def name(self) -> Text:
        return "action_update_address"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[EventType]:

        address_street = tracker.get_slot("address_street")
        address_city = tracker.get_slot("address_city")
        address_state = tracker.get_slot("address_state")
        address_zip = tracker.get_slot("address_zip")

        address_line_two = f"{address_city}, {address_state} {address_zip}"
        full_address = "\n".join([address_street, address_line_two])

        dispatcher.utter_message(
            "Thank you! Your address has been changed to:")
        dispatcher.utter_message(full_address)

        # Update the address in the data.
        MOCK_DATA["member_info"]["home_address"] = {
            "address_street": address_street,
            "address_city": address_city,
            "address_state": address_state,
            "address_zip": address_zip
        }

        return [SlotSet("verify_address", None)]


class ValidateChangeAddressForm(FormValidationAction):
    """Validates the user has filled out the change of address form correctly."""

    def name(self) -> Text:
        return "validate_change_address_form"

    async def validate_address_state(
            self,
            slot_value: Text,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:

        if isinstance(slot_value, list):
            slot_value = slot_value[-1]

        if slot_value.upper() not in US_STATES:
            dispatcher.utter_message(
                f"{slot_value} is invalid. Please provide a valid state.")
            return {"address_state": None}

        return {"address_state": slot_value}


# New ID Card Actions

class ActionNewIdCard(Action):

    def name(self) -> Text:
        return "action_new_id_card"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[EventType]:

        dispatcher.utter_message("Thank you! We'll send you a new ID card.")

        return []


class ActionRecentClaims(Action):

    def name(self) -> Text:
        return "action_ask_recent_claims"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:

        # Get the claims on the page.
        claim_page = tracker.get_slot("page")

        # Get the first initial page of claims.
        if claim_page is None:
            scroll_response = claims_scroll(claim_page, "init")
        else:
            scroll_response = claims_scroll(claim_page, "next")

        for c in scroll_response["claims"]:
            dispatcher.utter_message(response="utter_claim_detail", **c)

        return [SlotSet("page", scroll_response["page"])]


# Get Status of Claim

class ActionClaimStatus(Action):
    """Gets the status of the user's last claim."""

    def name(self) -> Text:
        """Unique identifier for the action."""
        return "action_claim_status"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:

        # Get the claim provided by the user.
        user_clm_id = tracker.get_slot("claim_id")
        clm = next((c for c in MOCK_DATA["claims"] if str(
            c["claim_id"]) == user_clm_id), None)

        # Display details about the selected claims.
        if clm:
            formatted_date = str(datetime.datetime.strptime(
                str(clm["claim_date"]), "%Y%m%d").date())
            clm_params = {
                "claim_date": formatted_date,
                "claim_id": clm["claim_id"],
                "claim_balance": f"${str(clm['claim_balance'])}",
                "claim_status": clm["claim_status"]
            }
            dispatcher.utter_message(
                response="utter_claim_detail", **clm_params)

            return [SlotSet("has_outstanding_balance", True)]

        else:
            dispatcher.utter_message("I don't know that claim...")

        return []


class ValidateGetClaimForm(FormValidationAction):
    """Validates data entered into the Get Claim Form."""

    def name(self) -> Text:
        """Unique identifier for the action."""
        return "validate_get_claim_form"

    async def validate_claim_id(
            self,
            value: Text,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Checks if the claim ID is valid for the member."""
        user_claims = MOCK_DATA["claims"]
        claim_id = tracker.get_slot("claim_id")

        # Sometimes slot is being double filled.
        if isinstance(claim_id, list):
            claim_id = next(tracker.get_latest_entity_values("claim_id"), None)

        if str(claim_id) not in [clm["claim_id"] for clm in user_claims]:
            dispatcher.utter_message(
                "The Claim ID you entered is not valid. Please check and try again.")
            return {"claim_id": None}
        else:
            return {"claim_id": claim_id}


class ValidateClaimStatusForm(FormValidationAction):
    """Validates data entered into the Claim Status Form."""

    def name(self) -> Text:
        """Unique identifier for the action."""
        return "validate_claim_status_form"

    async def required_slots(
        self,
        slots_mapped_in_domain: List[Text],
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Optional[List[Text]]:
        additional_slots = []

        # If a member knows their claim ID then ask them. Otherwise, show them the status of some recent claims.
        if tracker.slots.get("knows_claim_id") == "/affirm":
            additional_slots.append("claim_id")
        elif tracker.slots.get("knows_claim_id") == "/deny":
            additional_slots.append("recent_claims")

        return additional_slots + slots_mapped_in_domain

    async def extract_recent_claims(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> Dict[Text, Any]:
        if tracker.slots["requested_slot"] == "recent_claims":
            text_of_last_user_message = tracker.latest_message.get("text")

            return {"recent_claims": text_of_last_user_message}

    async def extract_claim_id(
            self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> Dict[Text, Any]:
        if tracker.slots["requested_slot"] == "claim_id":
            print("entity", tracker.get_latest_entity_values("claim_id"))
            text_of_last_user_message = tracker.latest_message.get("text")

            return {"claim_id": text_of_last_user_message}

    async def validate_claim_id(
            self,
            value: Text,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Checks if the claim ID is valid for the member."""
        valid_claims = [
            "123456",
            "234567"
        ]
        claim_id = tracker.get_slot("claim_id")

        print("claim other validate", claim_id)

        if str(claim_id) not in valid_claims:
            dispatcher.utter_message(
                "The Claim ID you entered is not valid. Please check and try again.")
            return {"claim_id": None}

        return {"claim_id": claim_id}


# File New Claim Actions

class ActionStopNewClaim(Action):
    """Stops quote form and clears collected data."""

    def name(self) -> Text:
        """Unique identifier for the action."""
        return "action_stop_new_claim_form"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Executes the action"""
        reset_slots = ["claim_amount_submit",
                       "confirm_file_new_claim", "number", "amount-of-money"]

        # Reset the slot values.
        return [SlotSet(slot, None) for slot in reset_slots]


class ActionFileNewClaimForm(Action):

    def name(self) -> Text:
        return "action_file_new_claim_form"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:

        if tracker.get_slot("confirm_file_new_claim") == "yes":
            # Submit a new claim.
            claim_id = "NC" + \
                "".join([str(random.randint(0, 9)) for i in range(6)])
            claim_obj = {
                "claim_id": claim_id,
                "claim_balance": tracker.get_slot("claim_amount_submit"),
                "claim_date": datetime.datetime.strftime(datetime.datetime.today(), "%Y%m%d"),
                "claim_status": "Pending"
            }

            MOCK_DATA["claims"].append(claim_obj)
            dispatcher.utter_message(
                f"Your claim has been submitted.\n\nFor reference the claim id is: {claim_id}")
        else:
            dispatcher.utter_message(
                "Ok. Submitting your claim has been canceled.")

        reset_slots = ["claim_amount_submit",
                       "confirm_file_new_claim",
                       "number",
                       "amount-of-money",
                       "AA_quote_insurance_type"]
        return [SlotSet(slot, None) for slot in reset_slots]


class ValidateFileNewClaimForm(FormValidationAction):

    def name(self) -> Text:
        return "validate_file_new_claim_form"

    def validate_AA_quote_insurance_type(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate insurance type value."""

        if slot_value.lower() not in ["health", "auto", "life", "home"]:
            dispatcher.utter_message("I can only provide quotes for home, health, life, or home insurance. "
                                     "Please choose one of those options.")
            return {"AA_quote_insurance_type": None}
        elif slot_value.lower() in ["health", "auto", "life", "home"]:
            return {"AA_quote_insurance_type": slot_value}

        return {"AA_quote_insurance_type": None}

    def validate_claim_amount_submit(
            self,
            value: Text,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:

        # Submitted amount must be a number.
        try:
            submitted_amount = float(value)
        except ValueError:
            dispatcher.utter_message(
                "You must submit a numeric value for the claim amount.")
            return {"claim_amount_submit": None}

        # Submitted amount must be greater than 0.
        try:
            assert submitted_amount > 0
        except AssertionError:
            dispatcher.utter_message(
                "The amount you are claiming must be greater than zero.")
            return {"claim_amount_submit": None}

        return {"claim_amount_submit": submitted_amount}


# Scroll Claims Action

class ActionScrollClaimsExit(Action):
    """Cleans up claim scrolling upon form exit."""

    def name(self) -> Text:
        return "action_scroll_claims_form_exit"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        reset_slots = ["scroll_status", "scroll_claims",
                       "page", "scroll_active_claim"]

        if tracker.get_slot("scroll_status") == "select":
            reset_slots = ["scroll_status", "scroll_claims",
                           "page", "scroll_active_claim"]

            return [SlotSet(s, None) for s in reset_slots] + [SlotSet("claim_id", tracker.get_slot("scroll_active_claim"))]
        elif tracker.get_slot("scroll_status") == "cancel":
            reset_slots = ["scroll_status", "scroll_claims",
                           "page", "scroll_active_claim"]
            return [SlotSet(s, None) for s in reset_slots] + [
                SlotSet("scroll_status", "cancel")]

        return [SlotSet(s, None) for s in reset_slots]


class ActionAskScrollClaims(Action):
    """Gets the status of the user's last claim."""

    def name(self) -> Text:
        """Unique identifier for the action."""
        return "action_ask_scroll_claims"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        # Get the claims on the page.
        claim_page = tracker.get_slot("page")
        scroll_status = tracker.get_slot("scroll_status")

        msg_template = "utter_scroll_status_prev_next"
        # Get the first initial page of claims.
        if claim_page is None:
            scroll_response = claims_scroll(claim_page, "init")
            msg_template = "utter_scroll_status_next"
        else:
            scroll_response = claims_scroll(claim_page, scroll_status)

        # Check if on last page.
        if scroll_response["is_last_page"]:
            msg_template = "utter_scroll_status_prev"
        elif scroll_response["page"] == 0:
            msg_template = "utter_scroll_status_next"

        dispatcher.utter_message(
            response="utter_claim_detail", **scroll_response["claims"])
        dispatcher.utter_message(response=msg_template)

        return [SlotSet("page", scroll_response["page"]),
                SlotSet("scroll_active_claim", scroll_response["claims"]["claim_id"])]


class ActionValidateScrollClaims(FormValidationAction):

    def name(self) -> Text:
        return "validate_scroll_claims_form"

    async def validate_scroll_claims(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:

        # Get the claims on the page.
        scroll_status = tracker.get_slot("scroll_status")

        if scroll_status == "cancel":
            print("validate scroll stop")
            return {"scroll_claims": "stop"}
        elif scroll_status == "select":
            print("validate scroll select")
            return {"scroll_claims": "select"}

        return {"scroll_claims": None}


# Pay Claim Actions

class ActionPayClaim(Action):
    """Gets the status of the user's last claim."""

    def name(self) -> Text:
        """Unique identifier for the action."""
        return "action_pay_claim"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        reset_slots = ["claim_balance", "amount-of-money",
                       "confirm_payment", "number", "claim_id", "claim_pay_amount"]

        # Get the claim provided by the user.
        user_clm_id = tracker.get_slot("claim_id")
        amount_to_pay = tracker.get_slot("claim_pay_amount")
        claim_balance = tracker.get_slot("claim_balance")

        if claim_balance == 0:
            dispatcher.utter_message(response="utter_zero_balance")
            reset_slots.append("claim_id")
            return [SlotSet(slot, None) for slot in reset_slots]

        msg_params = {
            "claim_id": user_clm_id,
            "amount_to_pay": amount_to_pay,
            "claim_balance": claim_balance - amount_to_pay
        }
        for c in MOCK_DATA["claims"]:
            if c["claim_id"] == user_clm_id:
                c.update({"claim_balance": claim_balance - amount_to_pay})

        dispatcher.utter_message(
            response="utter_claim_payment_success", **msg_params)

        return [SlotSet(slot, None) for slot in reset_slots]


class ActionCancelPayment(Action):
    """Cancels the payment form."""

    def name(self) -> Text:
        return "action_cancel_payment"

    async def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> List[Dict]:
        dispatcher.utter_message(response="utter_cancel_payment")

        reset_slots = ["claim_balance", "claim_pay_amount",
                       "claim_id", "confirm_payment", "amount-of-money", "number"]
        return [SlotSet(slot, None) for slot in reset_slots]


class ValidatePayClaimForm(FormValidationAction):

    def name(self) -> Text:
        return "validate_pay_claim_form"

    async def required_slots(
            self,
            slots_mapped_in_domain: List[Text],
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
    ) -> Optional[List[Text]]:

        if tracker.get_slot("claim_balance") == 0:
            return []

        return slots_mapped_in_domain

    async def extract_amount_of_money(
            self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ):
        # Check if the user provided a proper dollar amount.
        if tracker.slots["requested_slot"] == "amount-of-money":
            amount_to_pay = None
            last_message = tracker.latest_message

            # Check contents of latest message before for a valid dollar amount.
            try:
                ent = next(
                    item for item in last_message["entities"] if item["entity"] == "amount-of-money")
                amount_to_pay = ent["value"]
                return {"amount-of-money": amount_to_pay}
            except StopIteration:
                pass

            try:
                ent = next(
                    item for item in last_message["entities"] if item["entity"] == "number")
                amount_to_pay = ent["value"]
                return {"amount-of-money": amount_to_pay}
            except StopIteration:
                pass

            return {"amount-of-money": amount_to_pay}

    def validate_claim_id(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Checks if the claim ID is valid for the member."""
        user_claims = MOCK_DATA["claims"]
        claim_id = tracker.get_slot("claim_id")

        if isinstance(claim_id, list):
            claim_id = claim_id[-1]

        if str(claim_id) not in [clm["claim_id"] for clm in user_claims]:
            dispatcher.utter_message(
                "The Claim ID you entered is not valid. Please check and try again.")
            return {"claim_id": None}

        clm = next((c for c in MOCK_DATA["claims"] if str(
            c["claim_id"]) == claim_id), None)
        if clm["claim_balance"] == 0:
            dispatcher.utter_message(f"Claim {claim_id} is fully paid.")

        return {"claim_id": claim_id, "claim_balance": clm["claim_balance"], "number": None}

    def validate_claim_pay_amount(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        if tracker.slots.get("requested_slot") == "claim_pay_amount":
            claim_id = tracker.get_slot("claim_id")
            payment_amount = tracker.get_slot("claim_pay_amount")
            clm = next((c for c in MOCK_DATA["claims"] if str(
                c["claim_id"]) == claim_id), None)

            # Check that a valid number is provided.
            try:
                payment_amount = float(payment_amount)
            except TypeError:
                dispatcher.utter_message(
                    "Please enter a valid number as your payment amount.")
                return {"claim_pay_amount": None}

            # Check that the payment is greater than zero.
            if payment_amount <= 0:
                dispatcher.utter_message(
                    "Your payment must be greater than $0.")
                return {"claim_pay_amount": None}

            # Check that the payment amount doesn't exceed the amount owed on the claim.
            if payment_amount > clm["claim_balance"]:
                dispatcher.utter_message(f"The amount you want to pay, ${str(payment_amount)}, is greater than the amount "
                                         f"owed, ${str(clm['claim_balance'])}")
                return {"claim_pay_amount": clm["claim_balance"], "claim_balance": clm["claim_balance"]}

            return {"claim_pay_amount": payment_amount, "claim_balance": clm["claim_balance"]}

        return {"claim_pay_amount": None}


def claims_scroll(curr_page, scroll_status):
    """Performs the query to get claims on the specified page."""
    if curr_page is None:
        curr_page = 0

    if scroll_status == "next":
        if curr_page >= 0:
            curr_page += 1
    elif scroll_status == "init":
        curr_page = 0
    else:
        if curr_page > 0:
            curr_page -= 1

    # Get claims on the page.
    page_claims = MOCK_DATA["claims"][curr_page]
    clm_params = {
        "claim_date": str(datetime.datetime.strptime(str(page_claims["claim_date"]), "%Y%m%d").date()),
        "claim_id": page_claims["claim_id"],
        "claim_balance": f"${str(page_claims['claim_balance'])}",
        "claim_status": page_claims["claim_status"]
    }

    return {"page": curr_page,
            "claims": clm_params,
            "is_last_page": curr_page + 1 >= len(MOCK_DATA["claims"])}


class NotifyNewpolicies(Action):

    def name(self) -> Text:

        return "notify_new_policies"

    async def run(
        self, dispatcher, tracker: Tracker, domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        policies = [policy["policy_name"]
                    for policy in NEW_POLICIES["hot_policies"]]
        dispatcher.utter_message(
            text=f"The hottest policy available is {policies[0]}")
        return []
