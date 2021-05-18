# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

# import re to validate emails
import re
import json # attachments
import base64 # attachments
from datetime import datetime

from recognizers_number import recognize_number, Culture
from recognizers_date_time import recognize_datetime

# attachments imports
from botbuilder.schema import (
    ChannelAccount,
    HeroCard,
    CardAction,
    ActivityTypes,
    Attachment,
    AttachmentData,
    Activity,
    ActionTypes,
)

# conversation builder imports
from botbuilder.core import (
    ActivityHandler,
    ConversationState,
    TurnContext,
    UserState,
    MessageFactory,
    CardFactory
)

from data_models import ConversationFlow, Question, UserProfile


class ValidationResult:
    def __init__(
        self, is_valid: bool = False, value: object = None, message: str = None
    ):
        self.is_valid = is_valid
        self.value = value
        self.message = message


class CustomPromptBot(ActivityHandler):
    def __init__(self, conversation_state: ConversationState, user_state: UserState):
        # Error handling
        if conversation_state is None: 
            raise TypeError(
                "[CustomPromptBot]: Missing parameter. conversation_state is required but None was given"
            )
        if user_state is None:
            raise TypeError(
                "[CustomPromptBot]: Missing parameter. user_state is required but None was given"
            )

        self.conversation_state = conversation_state
        self.user_state = user_state

        self.flow_accessor = self.conversation_state.create_property("ConversationFlow")
        self.profile_accessor = self.user_state.create_property("UserProfile")

    async def on_message_activity(self, turn_context: TurnContext):
        # Get the state properties from the turn context.
        profile = await self.profile_accessor.get(turn_context, UserProfile)
        flow = await self.flow_accessor.get(turn_context, ConversationFlow)

        await self._fill_out_user_profile(flow, profile, turn_context)

        # Save changes to UserState and ConversationState
        await self.conversation_state.save_changes(turn_context)
        await self.user_state.save_changes(turn_context)

    async def _fill_out_user_profile(
        self, flow: ConversationFlow, profile: UserProfile, turn_context: TurnContext):
        # Begins flow process
        user_input = turn_context.activity.text.strip()

        # Ask for date; starts conversation flow
        if flow.last_question_asked == Question.NONE:
            await turn_context.send_activity(
                MessageFactory.text("Let's get started. What date and time would you like to book your movie for?")
            )
            flow.last_question_asked = Question.DATE

        # Validate date; ask for movie selection
        elif flow.last_question_asked == Question.DATE:
            # This is where date must be bound to profile.date
            validate_result = self._validate_date(user_input)
            if not validate_result.is_valid:
                await turn_context.send_activity(
                    MessageFactory.text(validate_result.message)
                )
            else:
                profile.date = validate_result.value
                await turn_context.send_activity(
                    MessageFactory.text(f"Great! We have a good selection of movies showing at {profile.date}")
                )
                
                await turn_context.send_activity(
                    MessageFactory.text("Which movie would you like to watch? Please type the name of the movie as your reply.")
                )
            # movies attachment
                message = Activity(type=ActivityTypes.message)
                message.text = "Moana, Once Upon a Time in Hollywood, Ready Player One, Sicario, The Girl With the Dragon Tattoo."
                message.attachments = [self._get_inline_attachment()]
                               
                await turn_context.send_activity(message)
                flow.last_question_asked = Question.MOVIE

        # Validate movie; ask for seat reservations
        elif flow.last_question_asked == Question.MOVIE:
            ## This is where movie must be bound to profile.movie
            validate_result = self._validate_movie(user_input)
            if not validate_result.is_valid:
                await turn_context.send_activity(
                    MessageFactory.text(validate_result.message)
                )
            else:
                profile.movie = validate_result.value
                await turn_context.send_activity(
                    MessageFactory.text(f"Sounds good! {profile.movie} is a great pick!")
                )
                await turn_context.send_activity(
                    MessageFactory.text("How many seats are you reserving?")
                )
                flow.last_question_asked = Question.SEATS

        # Validate seats; ask about row preferences

        elif flow.last_question_asked == Question.SEATS:
            validate_result = self._validate_seats(user_input)
            if not validate_result.is_valid:
                await turn_context.send_activity(
                    MessageFactory.text(validate_result.message)
                )
            else:
                profile.seats = validate_result.value
                await turn_context.send_activity(
                    MessageFactory.text(f"You are booking {profile.seats} seats.")
                )
                await turn_context.send_activity(
                    MessageFactory.text("What is your row preference? There are 50 rows in our theater.")
                )
                flow.last_question_asked = Question.PREFERENCE

        # Validate preferences; ask about email

        elif flow.last_question_asked == Question.PREFERENCE:
            validate_result = self._validate_preference(user_input)
            if not validate_result.is_valid:
                await turn_context.send_activity(
                    MessageFactory.text(validate_result.message)
                )
            else:
                profile.preference = validate_result.value
                await turn_context.send_activity(
                    MessageFactory.text(f"Your row preference has been set as {profile.preference}")
                )
                await turn_context.send_activity(
                    MessageFactory.text("Please enter your email for booking confirmation.")
                )
                flow.last_question_asked = Question.EMAIL

        # Validate email, confirm by displaying all info, wrap up w/ NONE
        elif flow.last_question_asked == Question.EMAIL:
            validate_result = self._validate_email(user_input)
            if not validate_result.is_valid:
                await turn_context.send_activity(
                    MessageFactory.text(validate_result.message)
                )
            else:
                profile.email = validate_result.value
                await turn_context.send_activity(
                    MessageFactory.text(
                        f"You have now completed the booking process."
                    )
                )
                await turn_context.send_activity(
                    MessageFactory.text(
                        f"Booking for {profile.email}: {profile.movie} on {profile.date}"
                    )
                )
                await turn_context.send_activity(
                    MessageFactory.text(
                        f"You are reserving {profile.seats} seats in row {profile.preference}"
                    )
                )
                await turn_context.send_activity(
                    MessageFactory.text("Type anything to run the bot again.")
                )
                flow.last_question_asked = Question.NONE #End of flow, able to restart again

    # Ensures valid text input by checking for more than one character
    def _validate_movie(self, user_input: str) -> ValidationResult:
        if not user_input:
            return ValidationResult(
                is_valid=False,
                message="Please enter a valid movie.",
            )

        return ValidationResult(is_valid=True, value=user_input)

    # Fetches and returns attachment
    def _get_inline_attachment(self) -> Attachment:
        """
        Attachment help:

        https://docs.microsoft.com/en-us/azure/bot-service/rest-api/bot-framework-rest-connector-add-rich-cards?view=azure-bot-service-4.0
        https://docs.microsoft.com/en-us/azure/bot-service/bot-builder-howto-add-media-attachments?view=azure-bot-service-4.0&tabs=csharp
        """
        path = "C:\\Users\\skimo\\botbuilder-samples\\samples\\python\\movie_booker\\resources\\44.prompt-for-user-input\\resources\\posters.png"
        with open(path, "rb") as in_file:
            base64_image = base64.b64encode(in_file.read()).decode()

            return Attachment(
            name="List of Movies",
            content_type="image/png",
            content_url=f"data:image/png;base64,{base64_image}",
        )

    # Validates seat selection by checking to make sure there are between 1 and 10 seats reserved
    def _validate_seats(self, user_input: str) -> ValidationResult:
        results = recognize_number(user_input, Culture.English)
        for result in results:
            if "value" in result.resolution:
                seats = int(result.resolution["value"])
                if 1 <= seats <= 10:
                    return ValidationResult(is_valid=True, value=seats)
        return ValidationResult(
            is_valid=False, message="Please enter between 1 and 10 seats."
        )

    # Validates row preference by checking to make sure row selected is between 1 and 50
    def _validate_preference(self, user_input: str) -> ValidationResult:
        results = recognize_number(user_input, Culture.English)
        ## COPY 2 WIN
        for result in results:
            if "value" in result.resolution:
                preference = int(result.resolution["value"])
                if 1 <= preference <= 50:
                    return ValidationResult(is_valid=True, value=preference)
        return ValidationResult(
            is_valid=False, message="Our theater only has 50 rows. Please enter a number in between 1 and 50."
        )    

    # Validates email by checking for email syntax structure against a regex
    def _validate_email(self, user_input: str) -> ValidationResult:
        email = user_input
        if re.search("^[\.\w-]+@([\w-]+\.)+[\w-]{2,4}$", email) != None:
            return ValidationResult(is_valid=True, value=email)
        return ValidationResult(
            is_valid=False, message="Please enter a valid email address"
        )

    # Validates date and time
    def _validate_date(self, user_input: str) -> ValidationResult:
        try:
            # Try to recognize the input as a date-time. This works for responses such as "11/14/2018", "9pm",
            # "tomorrow", "Sunday at 5pm", and so on. The recognizer returns a list of potential recognition results,
            # if any.
            results = recognize_datetime(user_input, Culture.English)
            for result in results:
                for resolution in result.resolution["values"]:
                    if "value" in resolution:
                        now = datetime.now()

                        value = resolution["value"]
                        if resolution["type"] == "date":
                            candidate = datetime.strptime(value, "%Y-%m-%d")
                        elif resolution["type"] == "time":
                            candidate = datetime.strptime(value, "%H:%M:%S")
                            candidate = candidate.replace(
                                year=now.year, month=now.month, day=now.day
                            )
                        else:
                            candidate = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")

                        # user response must be more than an hour out

                        diff = candidate - now
                        if diff.total_seconds() >= 3600:
                            return ValidationResult(
                                is_valid=True,
                                value=candidate.strftime("%m/%d/%y at %H:%M"),
                            )

            return ValidationResult(
                is_valid=False,
                message="I'm sorry, please enter a valid date.", 
            )
        except ValueError:
            return ValidationResult(
                is_valid=False,
                message="I'm sorry, I could not interpret that as an appropriate "
                "date. Please enter a date at least an hour out.",
            )

