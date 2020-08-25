from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.messages.flat.QuickChatSelection import QuickChatSelection
from rlbot.utils.structures.game_data_struct import GameTickPacket

from util.ball_prediction_analysis import find_slice_at_time
from util.boost_pad_tracker import BoostPadTracker
from util.drive import steer_toward_target
from util.sequence import Sequence, ControlStep
from util.vec import Vec3


class MyBot(BaseAgent):

    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.active_sequence: Sequence = None
        self.boost_pad_tracker = BoostPadTracker()
        self.boost_count = 0

    def initialize_agent(self):
        # Set up information about the boost pads now that the game is active and the info is available
        self.boost_pad_tracker.initialize_boosts(self.get_field_info())

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        """
        This function will be called by the framework many times per second. This is where you can
        see the motion of the ball, etc. and return controls to drive your car.
        """

        # Keep our boost pad info updated with which pads are currently active
        self.boost_pad_tracker.update_boost_status(packet)

        # This is good to keep at the beginning of get_output. It will allow you to continue
        # any sequences that you may have started during a previous call to get_output.
        if self.active_sequence and not self.active_sequence.done:
            controls = self.active_sequence.tick(packet)
            if controls is not None:
                return controls

        # Gather some information about our car and the ball
        my_car = packet.game_cars[self.index]
        car_location = Vec3(my_car.physics.location)
        car_velocity = Vec3(my_car.physics.velocity)
        ball_location = Vec3(packet.game_ball.physics.location)

        if car_location.dist(ball_location) > 1500:
            # We're far away from the ball, let's try to lead it a little bit
            ball_prediction = self.get_ball_prediction_struct()  # This can predict bounces, etc
            ball_in_future = find_slice_at_time(ball_prediction, packet.game_info.seconds_elapsed + 2)
            target_location = Vec3(ball_in_future.physics.location)
            self.renderer.draw_line_3d(ball_location, target_location, self.renderer.cyan())
        else:
            target_location = ball_location

        # Draw some things to help understand what the bot is thinking
        self.renderer.draw_line_3d(car_location, target_location, self.renderer.white())
        self.renderer.draw_string_3d(car_location, 1, 1, f'Speed: {car_velocity.length():.1f}', self.renderer.white())
        self.renderer.draw_rect_3d(target_location, 8, 8, True, self.renderer.cyan(), centered=True)

        if 750 < car_velocity.length() < 800:
            # We'll do a front flip if the car is moving at a certain speed.
            # Note: maybe do a diagonal / sideflip again? We should also only conditionally flip
            #  since getting caught mid flip is bad
            return self.begin_front_flip(packet)

        controls = SimpleControllerState()

        self.boost_steal(controls, car_location, my_car)

        return controls

    def available_big_boost(full_boosts):
        if (full_boosts.is_active == True):
            return True
        else:
            return False

    def boost_steal(self, controls, car_location, my_car):
        active_boosts = [boost for boost in self.boost_pad_tracker.get_full_boosts() if boost.is_active == True]
        car_x = int(car_location.x)
        car_y = int(car_location.y)

        boost_distances = []

        for boost in active_boosts:
            boost_x = int(boost.location.x)
            boost_y = int(boost.location.y)

            distance_from_boost = abs(boost_x - car_x) + abs(boost_y - car_y)
            boost_distances.append(distance_from_boost)

        boost_index = boost_distances.index(min(boost_distances))

        boost_location = active_boosts[boost_index].location

        close_enough = [boost_location[0] - 100,
                        boost_location[0] + 100,
                        boost_location[1] - 100,
                        boost_location[1] + 100]

        if close_enough[0] <= car_location[0] <= close_enough[1]:
            if close_enough[2] <= car_location[1] <= close_enough[3]:
                self.boost_count += 1

        controls.steer = steer_toward_target(my_car, boost_location)
        controls.throttle = 1.0

        if my_car.boost >= 80:
            controls.boost = True
        else:
            controls.boost = False

    def begin_front_flip(self, packet):
        # Send some quickchat just for fun
        self.send_quick_chat(team_only=False, quick_chat=QuickChatSelection.Information_IGotIt)

        # Do a front flip. We will be committed to this for a few seconds and the bot will ignore other
        # logic during that time because we are setting the active_sequence.
        self.active_sequence = Sequence([
            ControlStep(duration=0.05, controls=SimpleControllerState(jump=True)),
            ControlStep(duration=0.05, controls=SimpleControllerState(jump=False)),
            ControlStep(duration=0.2, controls=SimpleControllerState(jump=True, pitch=-1)),
            ControlStep(duration=0.8, controls=SimpleControllerState()),
        ])

        # Return the controls associated with the beginning of the sequence so we can start right away.
        return self.active_sequence.tick(packet)
