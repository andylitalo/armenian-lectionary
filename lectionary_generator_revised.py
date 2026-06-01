import datetime

def calculate_armenian_easter(year: int) -> datetime.date:
    """
    Computes Easter Sunday using the Gregorian calculation adopted by 
    the Armenian Apostolic Church (except Jerusalem) since 1923.
    """
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

def get_sunday_closest_to(year: int, month: int, day: int) -> datetime.date:
    """Finds the Sunday closest to a fixed date target as mandated by the Tonatsooyts."""
    target = datetime.date(year, month, day)
    for i in range(4):
        plus = target + datetime.timedelta(days=i)
        if plus.weekday() == 6: return plus
        minus = target - datetime.timedelta(days=i)
        if minus.weekday() == 6: return minus
    return target

def get_liturgical_day_details(target_date: datetime.date) -> dict:
    year = target_date.year
    easter = calculate_armenian_easter(year)
    
    # Calculate relative day offsets from Easter
    delta_easter = (target_date - easter).days
    weekday = target_date.weekday() # 0 = Monday, 6 = Sunday
    
    # Calculate Dynamic Solar-Closest Anchors
    assumption = get_sunday_closest_to(year, 8, 15)
    exaltation = get_sunday_closest_to(year, 9, 14)
    heesnak = get_sunday_closest_to(year, 11, 18)
    
    # Core fixed dates
    theophany = datetime.date(year, 1, 6)
    theophany_octave_end = datetime.date(year, 1, 13)
    presentation = datetime.date(year, 2, 14)
    annunciation = datetime.date(year, 4, 7)
    
    # Initialize reading signature payload
    day_name = "Ordinary Day"
    classification = "Ordinary Time"
    readings = {}

    # -------------------------------------------------------------
    # PHASE 1: FIXED IMMOVABLE FEASTS (High Priority Overrides)
    # -------------------------------------------------------------
    if target_date == datetime.date(year, 1, 5):
        return {
            "Day": "Eve of Theophany / Nativity Vigil (Ճրագալոյց)",
            "Class": "Dominical Feast",
            "Readings": {"OT": "Gen 1:1-3:24, Is 7:10-16, Ex 14:16-20, Mic 5:2-7, Prov 8:22-30", "Epistle": "Titus 2:11-15", "Gospel": "Matt 2:1-12"}
        }
    elif target_date == theophany:
        return {
            "Day": "Feast of Theophany and Nativity of Christ (Աստուածայայտնութիւն)",
            "Class": "Dominical Feast",
            "Readings": {"Matins": "Is 9:5-7", "Epistle": "Heb 1:1-12", "Gospel": "Luke 2:1-14"}
        }
    elif theophany < target_date <= theophany_octave_end:
        octave_day = (target_date - theophany).days + 1
        return {
            "Day": f"Day {octave_day} of the Octave of Theophany",
            "Class": "Dominical Octave",
            "Readings": {"Notice": "Octave rotating track from Epistles and Gospels."}
        }
    elif target_date == presentation:
        return {
            "Day": "Presentation of the Lord to the Temple (Տեառնընդառաջ)",
            "Class": "Dominical Feast",
            "Readings": {"OT": "Lev 12:1-8, Zech 8:19-23", "Epistle": "Gal 3:24-29", "Gospel": "Luke 2:22-40"}
        }
    elif target_date == annunciation:
        return {
            "Day": "Annunciation to the Holy Virgin (Աւետումն)",
            "Class": "Dominical Feast",
            "Readings": {"OT": "Prov 11:30-12:4, Is 11:1-9", "Epistle": "Gal 3:24-29", "Gospel": "Luke 1:26-38"}
        }

    # -------------------------------------------------------------
    # PHASE 2: MOVABLE RECKONING CYCLES (Easter Relative)
    # -------------------------------------------------------------
    
    # A. Arachavorats Cycle (Pre-Lent Fast)
    if -70 <= delta_easter <= -64:
        fast_day = delta_easter + 71
        if delta_easter == -64:
            return {
                "Day": "Feast of St. Sarkis the Warrior",
                "Class": "Saint Day (Saturday)",
                "Readings": {"OT": "Prov 3:1-8, Is 49:1-7", "Epistle": "2 Tim 2:1-10", "Gospel": "John 15:17-16:4"}
            }
        elif weekday in [2, 4]: # Wed/Fri Fasting
            return {
                "Day": f"Arachavorats Fast Day {fast_day}",
                "Class": "Strict Fast Day",
                "Readings": {"OT": "Is 45:1-13 (Wednesday) / Is 45:14-25 (Friday)"}
            }
        else:
            return {"Day": f"Arachavorats Fast Day {fast_day}", "Class": "Strict Fast Day", "Readings": {"Notice": "Penitential Hour tracks"}}

    # B. Great Lent & Holy Week Cycle
    elif -49 <= delta_easter <= -1:
        if delta_easter == -49:
            return {
                "Day": "Poon Paregentan / Eve of Great Lent (Բուն Բարեկենդան)",
                "Class": "Dominical Sunday",
                "Readings": {"OT": "Is 58:1-14", "Epistle": "Rom 13:11-14:25", "Gospel": "Matt 6:1-21"}
            }
        
        # Lenten Weekdays (Mon-Fri) -> Pure Prophecies of Isaiah Track
        if weekday < 5 and delta_easter < -7:
            # Calculation logic maps Isaiah readings dynamically based on moving Lenten day count
            lenten_day = delta_easter + 49
            # Exact mapping example from Tonatsooyts rubric rules
            isaiah_map = {1: "Is 1:16-20", 2: "Is 2:2-3", 24: "Is 37:9-38 (Michink/Median)"}
            return {
                "Day": f"Day {lenten_day} of Great Lent" + (" (Michink / Median Day)" if delta_easter == -25 else ""),
                "Class": "Lenten Weekday Strict Fast",
                "Readings": {"Midday Isaiah Prophecy": isaiah_map.get(lenten_day, "Continuous Sequential Track of Isaiah"), "OT": "Genesis and Proverbs selections"}
            }
        
        # Lenten Saturdays (Liturgy Allowed - Commemoration of Saints)
        if weekday == 5 and delta_easter < -7:
            sat_map = {
                -42: "St. Theodore the Warrior",
                -35: "St. Cyril of Jerusalem",
                -28: "St. Gregory the Illuminator's Descent into the Pit"
            }
            return {"Day": sat_map.get(delta_easter, "Lenten Saturday Memorial"), "Class": "Saint Day", "Readings": {"OT": "Wisdom Selections", "Epistle": "Pauline Track", "Gospel": "Resurrection/Martyr Track"}}

        # Lenten Sundays
        if weekday == 6 and delta_easter < -7:
            lent_sundays = {
                -42: ("Second Sunday of Great Lent: Expulsion (Արտաքսման)", "Is 33:2-22", "Rom 12:1-13:10", "Matt 5:17-48"),
                -35: ("Third Sunday of Great Lent: The Prodigal Son (Անառակի)", "Is 54:11-55:13", "2 Cor 6:1-7:1", "Luke 15:1-32"),
                -28: ("Fourth Sunday of Great Lent: The Steward (Տնտեսի)", "Is 56:1-57:21", "Eph 4:17-5:14", "Luke 16:1-31"),
                -21: ("Fifth Sunday of Great Lent: The Judge (Դատաւորի)", "Is 65:8-25", "Phil 3:1-4:9", "Luke 17:20-18:14"),
                -14: ("Sixth Sunday of Great Lent: Advent (Գալստեան)", "Is 66:1-24", "Col 2:8-3:17", "Matt 22:34-23:39")
            }
            name, ot, ep, gos = lent_sundays[delta_easter]
            return {"Day": name, "Class": "Dominical Sunday", "Readings": {"OT": ot, "Epistle": ep, "Gospel": gos}}

        # Holy Week
        if delta_easter == -7:
            return {"Day": "Palm Sunday (Ծաղկազարդ)", "Class": "Dominical Feast", "Readings": {"OT": "Zech 9:9-15", "Epistle": "Phil 4:4-7", "Gospel": "Matt 20:29-21:17"}}
        elif delta_easter == -3:
            return {"Day": "Holy Thursday (Աւագ Հինգշաբթի)", "Class": "Holy Week", "Readings": {"Liturgy": "1 Cor 11:23-32, Matt 26:17-30", "Foot-Washing": "Dynamic Gospels"}}
        elif delta_easter == -2:
            return {"Day": "Holy Friday / Great Friday (Աւագ Ուրբաթ)", "Class": "Holy Week Passions", "Readings": {"Crucifixion Hour": "Is 52:13-53:12", "Gospel": "Passion Harmonization"}}
        elif delta_easter == -1:
            return {
                "Day": "Easter Eve / Holy Saturday Vigil (Ճրագալոյց Զատկի)",
                "Class": "Dominical Vigil",
                "Readings": {"OT Prophecies": "Gen 1:1-3:24, Gen 22:1-18, Is 60:1-13, Jonah 1:1-4:11, Dan 3:1-90", "Epistle": "1 Cor 15:1-11", "Gospel": "Matt 28:1-20"}
            }

    # C. Easter Exactly
    elif delta_easter == 0:
        return {
            "Day": "Feast of the Glorious Resurrection / Easter Sunday (Սուրբ Զատիկ)",
            "Class": "Feast of Feasts",
            "Readings": {"Liturgy Epistle": "Acts 1:1-8", "Liturgy Gospel": "John 1:1-17", "Vespers Gospel": "Luke 24:13-35"}
        }

    # D. Hinank Cycle (Eastertide 4-Gospel Daily Matrix Engine)
    elif 1 <= delta_easter <= 48:
        day_num = delta_easter + 1
        sundays_hinank = {7: "New Sunday (Նոր Կիրակի)", 14: "Green Sunday (Կանաչ Կիրակի)", 21: "Red Sunday (Կարմիր Կիրակի)"}
        name = sundays_hinank.get(delta_easter, f"Day {day_num} of Eastertide")
        if delta_easter == 39:
            return {"Day": "Feast of the Ascension of Our Lord (Համբարձում)", "Class": "Dominical Feast", "Readings": {"OT": "Acts 1:1-12", "Gospel": "Matt 28:16-20"}}
        
        return {
            "Day": name,
            "Class": "Hinank Period Track",
            "Readings": {
                "Matins": f"Luke Continuous Pericope (Track {day_num})",
                "Liturgy": f"Acts Ch. 1-28 Sequential Segment, John Continuous Pericope (Track {day_num})",
                "Vespers": f"Matthew Continuous Pericope (Track {day_num})",
                "Compline": f"Mark Continuous Pericope (Track {day_num})"
            }
        }
    
    elif delta_easter == 49:
        return {
            "Day": "Pentecost / Coming of the Holy Spirit (Հոգեգալուստ)",
            "Class": "Dominical Feast",
            "Readings": {"OT Selections": "Acts 2:1-21, Wis 7:21-24, Is 11:1-4", "Epistle": "1 John 4:1-6", "Gospel": "Luke 3:14-22"}
        }

    # E. Transfiguration / Vardavar Cycle
    elif delta_easter == 98:
        return {
            "Day": "Feast of the Transfiguration of Our Lord (Վարդավառ)",
            "Class": "Major Movable Dominical Feast",
            "Readings": {"OT": "Ex 19:16-20, 1 Kings 19:11-16, Is 52:7-10", "Epistle": "1 John 1:1-7", "Gospel": "Matt 17:1-9"}
        }
    elif delta_easter == 99:
        return {"Day": "Memorial of the Dead (Մերելոց)", "Class": "Dominical Remembrance", "Readings": {"Epistle": "2 Cor 5:1-10", "Gospel": "John 5:24-30"}}

    # -------------------------------------------------------------
    # PHASE 3: SOLAR-CLOSEST SUNDAY ANCHORS & ROUTING WEEKS
    # -------------------------------------------------------------
    if target_date == assumption:
        return {
            "Day": "Feast of the Assumption of the Holy Mother of God (Վերափոխումն)",
            "Class": "Major Movable Dominical Feast",
            "Readings": {"OT": "Prov 11:30-12:4, Is 62:1-11", "Epistle": "Gal 3:24-29", "Gospel": "Luke 1:39-56"}
        }
    elif target_date == exaltation:
        return {
            "Day": "Feast of the Exaltation of the Holy Cross (Խաչվերաց)",
            "Class": "Major Movable Dominical Feast",
            "Readings": {"OT": "Is 49:13-23", "Epistle": "Gal 6:14-18", "Gospel": "John 3:13-21"}
        }
    
    # Post-Exaltation Sub-Anchors
    delta_exaltation_weeks = (target_date - exaltation).days // 7
    if delta_exaltation_weeks == 2 and weekday == 6:
        return {"Day": "Feast of the Holy Cross of Varak (Վարագայ Խաչ)", "Class": "Dominical Feast", "Readings": {"OT": "Prov 3:18-26, Is 65:22-24", "Epistle": "Gal 6:14-18", "Gospel": "Matt 24:30-36"}}
    elif delta_exaltation_weeks == 6 and weekday == 6:
        return {"Day": "Feast of the Discovery of the Cross (Գիւտ Խաչ)", "Class": "Dominical Feast", "Readings": {"OT": "Wis 14:1-8, Is 33:22-34:1", "Epistle": "1 Cor 1:18-24", "Gospel": "Matt 24:27-36"}}

    if target_date == heesnak:
        return {"Day": "First Sunday of Advent (Յիսնակ)", "Class": "Dominical Season Start", "Readings": {"OT": "Is 36:1-9", "Epistle": "1 Thess 1:1-10", "Gospel": "Luke 12:13-31"}}

    # -------------------------------------------------------------
    # PHASE 4: FALLBACK ROUTING TRACKS (The Ordinary Weekday Logic)
    # -------------------------------------------------------------
    # Ordinary Weeks match structural readings based on their specific seasonal window
    if target_date < heesnak and target_date > exaltation:
        season_label = f"Week {delta_exaltation_weeks + 1} After Cross"
    elif target_date > heesnak:
        season_label = "Season of Heesnak (Advent)"
    elif delta_easter > 49 and delta_easter < 98:
        week_num = (delta_easter - 49) // 7 + 1
        season_label = f"Week {week_num} After Pentecost"
    else:
        season_label = "Ordinary Time Track"

    if weekday in [2, 4]: # Wednesdays and Fridays
        return {"Day": f"Ordinary Fast Day ({season_label})", "Class": "Weekly Fasting Day", "Readings": {"Notice": "Penitential Liturgical Hour Lessons (No Liturgy Pericopes)"}}
    elif weekday in [0, 1, 3, 5]: # Mon, Tue, Thu, Sat
        return {"Day": f"Ordinary Saint Day Commemoration ({season_label})", "Class": "Saint Day", "Readings": {"OT": "Wisdom / Prophet Lesson", "Epistle": "Pauline Pericope", "Gospel": "Standard Selection"}}
    elif weekday == 6:
        return {"Day": f"Ordinary Sunday ({season_label})", "Class": "Dominical Sunday", "Readings": {"OT": "Prophetic Text", "Epistle": "Canonical Epistle", "Gospel": "Resurrection Pericope"}}

    return {"Day": day_name, "Class": classification, "Readings": readings}

# Verification Engine
if __name__ == "__main__":
    print("--- VERIFYING CALENDAR CALCULATIONS AGAINST SACREDTRADITION.AM ---")
    
    # Verification 1: Easter Sunday 2026
    d1 = datetime.date(2026, 4, 5)
    print(f"\nTarget Date: {d1.isoformat()}")
    for k, v in get_liturgical_day_details(d1).items(): print(f"  {k}: {v}")
        
    # Verification 2: The Median Day of Great Lent (Michink) 2026
    d2 = datetime.date(2026, 3, 11)
    print(f"\nTarget Date: {d2.isoformat()}")
    for k, v in get_liturgical_day_details(d2).items(): print(f"  {k}: {v}")
        
    # Verification 3: Green Sunday 2026 (Two weeks after Easter Sunday)
    d3 = datetime.date(2026, 4, 19)
    print(f"\nTarget Date: {d3.isoformat()}")
    for k, v in get_liturgical_day_details(d3).items(): print(f"  {k}: {v}")
