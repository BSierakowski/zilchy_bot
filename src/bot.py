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
        self.airborne = False

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

        # if car_location.dist(ball_location) > 1500:
        #     # We're far away from the ball, let's try to lead it a little bit
        #     ball_prediction = self.get_ball_prediction_struct()  # This can predict bounces, etc
        #     ball_in_future = find_slice_at_time(ball_prediction, packet.game_info.seconds_elapsed + 2)
        #     target_location = Vec3(ball_in_future.physics.location)
        #     self.renderer.draw_line_3d(ball_location, target_location, self.renderer.cyan())
        # else:
        #     target_location = ball_location

        # Draw some things to help understand what the bot is thinking
        # self.renderer.draw_line_3d(car_location, target_location, self.renderer.white())
        # self.renderer.draw_string_3d(car_location, 1, 1, f'Speed: {car_velocity.length():.1f}', self.renderer.white())
        # self.renderer.draw_rect_3d(target_location, 8, 8, True, self.renderer.cyan(), centered=True)

        controls = SimpleControllerState()

        # if 750 < car_velocity.length() < 800:
        #     # We'll do a front flip if the car is moving at a certain speed.
        #     # Note: maybe do a diagonal / sideflip again? We should also only conditionally flip
        #     #  since getting caught mid flip is bad, this would also be cool as a wavedash
        #     return self.begin_front_flip(packet)
        #
        # if my_car.is_super_sonic == False:
        #     controls.boost = True
        #
        # if my_car.boost == 100:
        #     controls.boost = True

        if my_car.has_wheel_contact == True:
            self.airborne = False
        else:
            # try to recover here
            if self.airborne == False:
                self.send_quick_chat(team_only=False, quick_chat=QuickChatSelection.Custom_Useful_Faking)

            self.airborne = True

        if self.ball_in_kickoff_position(ball_location, packet):
            self.kickoff_active = True
        else:
            self.kickoff_active = False
            self.kickoff_position = None

        if self.kickoff_active and self.kickoff_position is None:
            self.kickoff_position = self.get_kickoff_position(car_location)

        if self.kickoff_active and self.kickoff_position is not None:
            self.do_kickoff(my_car, car_location, car_velocity, ball_location, controls, packet)


        # self.boost_steal(controls, car_location, my_car, ball_location)
        # self.half_flip_sequence(packet)
        # self.ball_chase(controls, my_car, ball_location)

        return controls

    def get_kickoff_position(self, car_location):
        if car_location.flat().dist(Vec3(2048.00, -2560.00)) < 50 or car_location.flat().dist(Vec3(-2048.00, 2560.00)) < 50:
            return 1
        elif car_location.flat().dist(Vec3(-2048.00, -2560.00)) < 50 or car_location.flat().dist(Vec3(2048.00, 2560.00)) < 50:
            return 2
        elif car_location.flat().dist(Vec3(256.00, -3840.00)) < 50 or car_location.flat().dist(Vec3(-256.00, 3840.00)) < 50:
            return 3
        elif car_location.flat().dist(Vec3(-256.00, -3840.00)) < 50 or car_location.flat().dist(Vec3(256.00, 3840.00)) < 50:
            return 4
        else:
            return 5

            and packet.game_ball.physics.velocity.x == 0 \
            and packet.game_ball.physics.velocity.y == 0 \
            and packet.game_ball.physics.velocity.z == 0:
                return True
        else:
            return False

    def do_kickoff(self, my_car, car_location, car_velocity, ball_location, controls, packet):
        self.send_quick_chat(team_only=False, quick_chat=QuickChatSelection.Information_Incoming)

        print(f"kickoff position {self.kickoff_position}")

        if self.kickoff_position == 1:
            self.left_speed_flip_kickoff(packet)

    def ball_chase(self, controls, my_car, ball_location):
        controls.steer = steer_toward_target(my_car, ball_location)
        controls.throttle = 1.0

    def half_flip_sequence(self, packet):
        self.active_sequence = Sequence([
            ControlStep(duration=0.3, controls=SimpleControllerState(throttle=-1)),
            ControlStep(duration=0.1, controls=SimpleControllerState(throttle=-1, jump=True, pitch=1)),
            ControlStep(duration=0.2, controls=SimpleControllerState(throttle=-1, jump=False, pitch=1)),
            ControlStep(duration=0.1, controls=SimpleControllerState(jump=True, pitch=1)),
            ControlStep(duration=0.1, controls=SimpleControllerState(throttle=1, boost=True, pitch=-1)),
            ControlStep(duration=0.5, controls=SimpleControllerState(throttle=1, boost=True, pitch=-1, roll=1)),
            ControlStep(duration=0.2, controls=SimpleControllerState(roll=0)),
            ControlStep(duration=0.5, controls=SimpleControllerState(throttle=1)),
        ])

        return self.active_sequence.tick(packet)



    def front_flip_kickoff(self, my_car, car_location, car_velocity, ball_location, controls, packet):
        self.send_quick_chat(team_only=False, quick_chat=QuickChatSelection.Information_Incoming)
        controls.steer = steer_toward_target(my_car, ball_location)
        controls.throttle = 1.0
        controls.boost = True

        distance_from_ball = car_location.dist(ball_location)

        # tweak these settings so the first and second flips go off at the right time
        if 750 < car_velocity.length() < 900:
            self.begin_front_flip(packet)

        if distance_from_ball <= 1000:
            self.begin_front_flip(packet)

    def boost_steal(self, controls, car_location, my_car, ball_location):
        active_boosts = [boost for boost in self.boost_pad_tracker.get_full_boosts() if boost.is_active == True]
        car_x = int(car_location.x)
        car_y = int(car_location.y)

        boost_distances = []

        for boost in active_boosts:
            boost_x = int(boost.location.x)
            boost_y = int(boost.location.y)

            distance_from_boost = abs(boost_x - car_x) + abs(boost_y - car_y)
            boost_distances.append(distance_from_boost)

        if len(active_boosts) == 0:
            controls.steer = steer_toward_target(my_car, ball_location)
            controls.throttle = 1.0
        else:
            boost_index = boost_distances.index(min(boost_distances))
            boost_location = active_boosts[boost_index].location

            controls.steer = steer_toward_target(my_car, boost_location)
            controls.throttle = 1.0

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
