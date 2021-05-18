# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.


class UserProfile:
    def __init__(self, date: str = None, movie: str = None, seats: int = 0,preference: str = None, email: str = None):
        self.date = date
        self.movie = movie
        self.seats = seats
        self.preference = preference
        self.email = email

