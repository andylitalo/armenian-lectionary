"""Armenian Church lectionary computation (Tonatsooyts rubric).

Pure, importable logic with no web/framework dependencies. The public entry
point is ``compute_armenian_lectionary(target_date)`` which returns a dict
describing the liturgical day and its scripture readings.
"""

import datetime


def calculate_gregorian_easter(year: int) -> datetime.date:
    """Computes Easter Sunday for any given year using the Meeus/Jones/Butcher algorithm."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    L = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * L) // 451
    month = (h + L - 7 * m + 114) // 31
    day = ((h + L - 7 * m + 114) % 31) + 1
    return datetime.date(year, month, day)


def get_closest_sunday(year: int, month: int, day: int) -> datetime.date:
    """Finds the Sunday closest to a fixed calendar target date per Tonatsooyts rubric."""
    target = datetime.date(year, month, day)
    for offset in range(4):
        plus_day = target + datetime.timedelta(days=offset)
        if plus_day.weekday() == 6:  # 6 represents Sunday in Python
            return plus_day
        minus_day = target - datetime.timedelta(days=offset)
        if minus_day.weekday() == 6:
            return minus_day
    return target


def compute_armenian_lectionary(target_date: datetime.date) -> dict:
    """
    Computes the liturgical name, day classification, and core scripture
    readings based on the rules of the Armenian Church Tonatsooyts.
    """
    year = target_date.year
    easter = calculate_gregorian_easter(year)
    delta = (target_date - easter).days
    weekday = target_date.weekday()  # 0 = Monday, 6 = Sunday

    # --- 1. FIXED IMMOVABLE FEASTS ---
    if target_date.month == 1 and target_date.day == 5:
        return {
            "Date": target_date.isoformat(),
            "Liturgical Day": "Eve of Theophany / Nativity Vigil (Ճրագալոյց Ծննդեան)",
            "Classification": "Fixed Dominical Feast",
            "Readings": {
                "Old Testament": "Gen 1:1-3:24, Is 7:10-16, Ex 14:16-20, Mic 5:2-7, Prov 8:22-30",
                "Epistle": "Titus 2:11-15",
                "Gospel": "Matt 2:1-12"
            }
        }
    elif target_date.month == 1 and target_date.day == 6:
        return {
            "Date": target_date.isoformat(),
            "Liturgical Day": "Theophany and Nativity of Christ (Աստուածայայտնութիւն)",
            "Classification": "Fixed Dominical Feast",
            "Readings": {
                "Old Testament / Matins": "Is 9:5-7",
                "Epistle": "Heb 1:1-12",
                "Gospel": "Luke 2:1-14"
            }
        }
    elif target_date.month == 4 and target_date.day == 7:
        return {
            "Date": target_date.isoformat(),
            "Liturgical Day": "Annunciation to the Holy Virgin (Աւետումն Սուրբ Աստուածածնի)",
            "Classification": "Fixed Dominical Feast",
            "Readings": {"Old Testament": "Prov 11:30-12:4, Is 11:1-9", "Epistle": "Gal 3:24-29", "Gospel": "Luke 1:26-38"}
        }

    # --- 2. MOVABLE LANDMARK SUNDAYS (Closest Sunday Calculations) ---
    assumption_sunday = get_closest_sunday(year, 8, 15)
    exaltation_sunday = get_closest_sunday(year, 9, 14)

    if target_date == assumption_sunday:
        return {
            "Date": target_date.isoformat(),
            "Liturgical Day": "Assumption of the Holy Mother of God (Վերափոխումն)",
            "Classification": "Major Movable Dominical Feast",
            "Readings": {"Old Testament": "Prov 11:30-12:4, Is 62:1-11", "Epistle": "Gal 3:24-29", "Gospel": "Luke 1:39-56"}
        }
    elif target_date == exaltation_sunday:
        return {
            "Date": target_date.isoformat(),
            "Liturgical Day": "Exaltation of the Holy Cross (Խաչվերաց)",
            "Classification": "Major Movable Dominical Feast",
            "Readings": {"Old Testament": "Is 49:13-23", "Epistle": "Gal 6:14-18", "Gospel": "John 3:13-21"}
        }

    # --- 3. EASTER-RELATIVE MOVABLE CYCLES ---

    # A. Great Lent and Holy Week Phase
    if -49 <= delta <= -1:
        if delta == -49:
            return {
                "Date": target_date.isoformat(),
                "Liturgical Day": "Poon Paregentan / Eve of Great Lent (Բուն Բարեկենդան)",
                "Classification": "Dominical Sunday",
                "Readings": {"Old Testament": "Is 58:1-14", "Epistle": "Rom 13:11-14:25", "Gospel": "Matt 6:1-21"}
            }

        # Lenten Weekdays: Mon to Fri (Focus on Midday Isaiah Prophecies)
        if weekday in [0, 1, 2, 3, 4] and delta < -7:
            # Demonstration samples of specific mapped days
            if delta == -48:  # 1st Day of Lent
                return {
                    "Date": target_date.isoformat(),
                    "Liturgical Day": "First Day of Great Lent",
                    "Classification": "Lenten Weekday Strict Fast",
                    "Readings": {
                        "Midday Prophecy (Isaiah)": "Is 1:16-20",
                        "Liturgical Note": "No Divine Liturgy celebrated. Readings belong to the Midday Hour."
                    }
                }
            elif delta == -44:  # Friday of the First Week
                return {
                    "Date": target_date.isoformat(),
                    "Liturgical Day": "Friday of the 1st Week of Lent",
                    "Classification": "Lenten Weekday Strict Fast",
                    "Readings": {
                        "Old Testament": "Deut 6:4-7:10, Job 6:13-7:13",
                        "Midday Prophecy (Isaiah)": "Is 40:1-8"
                    }
                }
            else:
                return {
                    "Date": target_date.isoformat(),
                    "Liturgical Day": f"Lenten Fast Day (Offset {delta})",
                    "Classification": "Lenten Weekday Strict Fast",
                    "Readings": {"Notice": "Midday Hour service features a rotating track of Genesis, Proverbs, and Isaiah Prophecies."}
                }

        # Lenten Sundays
        if weekday == 6 and delta < -1:
            lent_sundays = {
                -42: ("Second Sunday of Great Lent: Expulsion (Արտաքսման)", "Is 33:2-22", "Rom 12:1-13:10", "Matt 5:17-48"),
                -35: ("Third Sunday of Great Lent: The Prodigal Son (Անառակի)", "Is 54:11-55:13", "2 Cor 6:1-7:1", "Luke 15:1-32"),
                -28: ("Fourth Sunday of Great Lent: The Steward (Տնտեսի)", "Is 56:1-57:21", "Eph 4:17-5:14", "Luke 16:1-31"),
                -21: ("Fifth Sunday of Great Lent: The Judge (Դատաւորի)", "Is 65:8-25", "Phil 3:1-4:9", "Luke 17:20-18:14"),
                -14: ("Sixth Sunday of Great Lent: Advent (Գալստեան)", "Is 66:1-24", "Col 2:8-3:17", "Matt 22:34-23:39"),
                -7: ("Palm Sunday (Ծաղկազարդ)", "Zech 9:9-15", "Phil 4:4-7", "Matt 20:29-21:17")
            }
            name, ot, ep, gos = lent_sundays[delta]
            return {
                "Date": target_date.isoformat(),
                "Liturgical Day": name,
                "Classification": "Dominical Sunday",
                "Readings": {"Old Testament": ot, "Epistle": ep, "Gospel": gos}
            }

        # Holy Week Vigil (Holy Saturday)
        if delta == -1:
            return {
                "Date": target_date.isoformat(),
                "Liturgical Day": "Easter Eve / Holy Saturday Vigil (Ճրագալոյց Զատկի)",
                "Classification": "Holy Week Dominical Vigil",
                "Readings": {
                    "Old Testament Prophecies": "Gen 1:1-3:24, Gen 22:1-18, Is 60:1-13, Jonah 1:1-4:11, Dan 3:1-90",
                    "Epistle": "1 Cor 15:1-11",
                    "Gospel": "Matt 28:1-20"
                }
            }

    # B. Easter Day Exactly
    elif delta == 0:
        return {
            "Date": target_date.isoformat(),
            "Liturgical Day": "Feast of the Glorious Resurrection / Easter Sunday (Սուրբ Զատիկ)",
            "Classification": "Feast of Feasts / Dominical",
            "Readings": {
                "Epistle (Liturgy)": "Acts 1:1-8",
                "Gospel (Liturgy)": "John 1:1-17",
                "Gospel (Vespers)": "Luke 24:13-35"
            }
        }

    # C. Hinank Cycle (Eastertide: 4-Gospel daily track)
    elif 1 <= delta <= 48:
        # Special Sunday designations within Hinank
        hinank_sundays = {7: "New Sunday (Նոր Կիրակի)", 14: "Green Sunday (Կանաչ Կիրակի)", 21: "Red Sunday (Կարմիր Կիրակի)"}
        day_name = hinank_sundays.get(delta, f"Day {delta + 1} of Eastertide")
        if delta == 39:
            day_name = "Feast of the Ascension of Our Lord (Համբարձում)"

        return {
            "Date": target_date.isoformat(),
            "Liturgical Day": day_name,
            "Classification": "Hinank Period (Continuous Paschal Joy)",
            "Readings": {
                "Morning (Matins)": "Continuous Pericope from LUKE",
                "Midday (Divine Liturgy)": "Acts [Sequential Verse Set], Continuous Pericope from JOHN",
                "Evening (Vespers)": "Continuous Pericope from MATTHEW",
                "Dismissal Service": "Continuous Pericope from MARK"
            }
        }

    elif delta == 49:
        return {
            "Date": target_date.isoformat(),
            "Liturgical Day": "Pentecost / Coming of the Holy Spirit (Հոգեգալուստ)",
            "Classification": "Dominical Feast",
            "Readings": {
                "Old Testament / Lessons": "Acts 2:1-21, Wis 7:21-24, Is 11:1-4",
                "Epistle": "1 John 4:1-6",
                "Gospel": "Luke 3:14-22"
            }
        }

    # --- 4. DEFAULT STANDALONE WEEKLY TRACK ---
    day_types = {0: "Saint Day", 1: "Saint Day", 2: "Fast Day (Ordinary)", 3: "Saint Day", 4: "Fast Day (Ordinary)", 5: "Saint Day", 6: "Dominical Sunday"}
    return {
        "Date": target_date.isoformat(),
        "Liturgical Day": f"Ordinary Cycle (Easter Offset: {delta})",
        "Classification": day_types[weekday],
        "Readings": {"Notice": "Determined via weekly numeric sequence downstream from Pentecost or Cross cycles."}
    }
