from pathlib import Path

from rlbottraining.common_exercises.kickoff_exercise import KickoffExercise, Spawns
from rlbot.matchconfig.match_config import PlayerConfig, Team


def make_default_playlist():
    exercises = [
        KickoffExercise('Straight', blue_spawns=[Spawns.STRAIGHT], orange_spawns=[]),
        KickoffExercise('Right Corner', blue_spawns=[Spawns.CORNER_R], orange_spawns=[]),
        KickoffExercise('Left Corner', blue_spawns=[Spawns.CORNER_L], orange_spawns=[]),
        KickoffExercise('Back Right', blue_spawns=[Spawns.BACK_R], orange_spawns=[]),
        KickoffExercise('Back Left', blue_spawns=[Spawns.BACK_L], orange_spawns=[])
    ]

    for exercise in exercises:
        exercise.match_config.player_configs = [
            PlayerConfig.bot_config(Path(__file__).absolute().parent.parent / 'src' / 'bot.cfg', Team.BLUE)
        ]

    return exercises
