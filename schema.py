# What we show the USER on the frontend, so they know what's available to ask about.
# Keep this short and friendly - no raw column names here.
AVAILABLE_METRICS = [
    "Goals",
    "Shots",
    "Expected goals (xG)",
    "Passes",
    "Assists",
    "Dribbles",
    "Tackles & duels",
    "Interceptions",
    "Fouls & cards",
    "Substitutions",
]

# What we give the AGENT, so it knows how to turn a question into SQL over the
# events table. This is the messy, technical version - raw column names and
# what condition on them means what.
COLUMN_GUIDE = """
The events table has one row per event. Useful columns:

- player.name, team.name, minute, second, period
- type.name: the kind of event. Common values: Pass, Shot, Carry, Dribble,
  Duel, Pressure, Interception, Clearance, Block, Foul Committed, Foul Won,
  Substitution, Ball Recovery, Dispossessed, Miscontrol

How to compute common metrics from these:

- Goals: type.name = 'Shot' and "shot.outcome.name" = 'Goal'
- Shots: type.name = 'Shot'
- Expected goals (xG): sum("shot.statsbomb_xg") where type.name = 'Shot'
- Passes: type.name = 'Pass'
- Completed passes: type.name = 'Pass' and "pass.outcome.name" is null
  (StatsBomb only fills pass.outcome.name when the pass did NOT succeed)
- Assists: "pass.goal_assist" = true
- Dribbles: type.name = 'Dribble'
- Tackles: type.name = 'Duel' and "duel.type.name" = 'Tackle'
- Interceptions: type.name = 'Interception'
- Fouls committed: type.name = 'Foul Committed'
- Cards: "foul_committed.card.name" is not null (values: Yellow Card, Red Card,
  Second Yellow)
- Substitutions: type.name = 'Substitution'

Column names with dots must be double-quoted in SQL, e.g. "shot.statsbomb_xg".
"""