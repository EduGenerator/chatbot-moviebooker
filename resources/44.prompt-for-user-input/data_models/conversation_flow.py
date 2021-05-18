# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from enum import Enum


class Question(Enum):
    DATE = 1
    MOVIE = 2
    SEATS = 3
    PREFERENCE = 4
    EMAIL = 5
    NONE = 6


class ConversationFlow:
    def __init__(
        self, last_question_asked: Question = Question.NONE,
    ):
        self.last_question_asked = last_question_asked
