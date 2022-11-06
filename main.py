import sys
import itertools
from dataclasses import dataclass
import numpy

DEBUG = True

MONSTER_TEAM = 0
MY_TEAM = 1
ENEMY_TEAM = 2

CLUELESS = (0, 0)
ROAMING_TOWARDS_ME = (0, 1)
ROAMING_TOWARDS_ENEMY = (0, 2)
TARGETING_ME = (1, 1)
TARGETING_ENEMY = (1, 2)

INITIAL_HP = 3
INITIAL_MANA = 0

ATTACK_RADIUS = 800
MONSTER_SPEED = 400
HERO_SPEED = 800
RADIUS_TO_TARGET_BASE = 5000

# Spells
SPELL_COST = 10

SPELL_WIND_RANGE = 1280
SPELL_WIND_STRENGTH = 2200

SPELL_SHIELD_RANGE = 2200
SPELL_SHIELD_EFFECT_PERIOD = 12  # measured in turns

SPELL_CONTROL_RANGE = 2200


class OutputFormatter:
    def __init__(self):
        self.actions = {}

    def action_move(self, hero: 'Hero', target_location: 'Point'):
        self.actions[hero.hero_id] = f"MOVE {target_location.x} {target_location.y}"

    def action_wait(self, hero: 'Hero'):
        self.actions[hero.hero_id] = "WAIT"

    def action_control(self, hero: 'Hero', entity_id: int, target_location: 'Point'):
        self.actions[hero.hero_id] = f'SPELL CONTROL {entity_id} {target_location.x} {target_location.y}'

    def action_wind(self, hero: 'Hero', target_location: 'Point'):
        self.actions[hero.hero_id] = f'SPELL WIND {target_location.x} {target_location.y}'

    def action_shield(self, hero: 'Hero', entity_id: int):
        self.actions[hero.hero_id] = f'SPELL SHIELD {entity_id}'

    def perform_action(self):
        actions = sorted(self.actions.items(), key=lambda action: action[0])  # List of tuples
        for _, command in actions:
            print(command)


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.array = numpy.array([x, y])

    def __repr__(self):
        return str((self.x, self.y))

    def get_distance_to(self, other) -> float:
        return numpy.linalg.norm(self.array - other.array)

    def __sub__(self, other):
        return Point(self.x - other.x, self.y - other.y)

    def __abs__(self):
        return Point(abs(self.x), abs(self.y))


TOP_LEFT = Point(0, 0)
BOTTOM_RIGHT = Point(17630, 9000)


class Game:
    formatter = OutputFormatter()

    def __init__(self, base_location, heroes_per_player):
        self.heroes_per_player = heroes_per_player

        self.my_base_location = base_location
        self.enemy_base_location = BOTTOM_RIGHT - base_location  # Because fu that's why

        self.my_hp = INITIAL_HP
        self.enemy_hp = INITIAL_HP
        self.my_mana = INITIAL_MANA
        self.enemy_mana = INITIAL_MANA

        self.heroes = []
        self.monsters = []

    def __repr__(self):
        return "\n".join(map(lambda attribute: f"{attribute[0]} = {attribute[1]}", self.__dict__.items()))

    def update_turn_data(self):
        self.my_hp, self.my_mana = [int(j) for j in input().split()]
        self.enemy_hp, self.enemy_mana = [int(j) for j in input().split()]

        entities = []
        entity_count = int(input())

        for i in range(entity_count):
            entities.append(build_entity_from_input())

        self.heroes = list(filter(lambda entity: isinstance(entity, Hero), entities))
        self.monsters = list(filter(lambda entity: isinstance(entity, Monster), entities))

    def handle_no_monsters(self):
        for hero, point in self.get_defensive_positions():
            self.formatter.action_move(hero, point)

    def perform_simple_attack(self):
        for hero in self.get_my_heroes():
            scary_monster = hero.get_most_dangerous_monster(self.get_dangerous_monsters((TARGETING_ME, ROAMING_TOWARDS_ME)), self.my_base_location)
            debug(f"Scary monster for Hero {hero.hero_id}: {scary_monster}")
            self.formatter.action_move(hero, scary_monster.location)

    def make_turn(self):
        if not self.get_dangerous_monsters((TARGETING_ME, ROAMING_TOWARDS_ME)):  # go to defensive positions if there are no monsters
            self.handle_no_monsters()
        else:
            assigned_heroes_for_control_spell = self.assign_heroes_to_monsters(
                self.get_monsters_near_heroes_dict(SPELL_CONTROL_RANGE))
            if not assigned_heroes_for_control_spell:
                self.perform_simple_attack()
            else:
                for hero_id, monster_id in assigned_heroes_for_control_spell.items():
                    if monster_id is None:
                        continue
                    self.formatter.action_control(self.get_entity_from_id(hero_id), monster_id,
                                                  self.enemy_base_location)
        self.formatter.perform_action()

    def get_targeting_monsters(self):
        return filter(lambda monster: monster.target == TARGETING_ME, self.monsters)

    def get_my_heroes(self):
        return sorted(filter(lambda hero: hero.team == MY_TEAM, self.heroes), key=lambda hero: hero.hero_id)

    def get_optimal_combination_heroes_to_points(self, heroes: list, points: list) -> list[tuple['Hero', Point]]:
        all_combinations = []

        list1_permutations = itertools.permutations(heroes, len(points))
        for each_permutation in list1_permutations:
            zipped = zip(each_permutation, points)
            all_combinations.append(list(zipped))

        def key_func(combinations: list[tuple[Hero, Point]]) -> float:
            """
            total score of a single combination, measured as the sum of distances from heroes to points
            :param combinations: list[tuple[Hero, Point]]
            :return: float
            """
            score = 0
            for combination in combinations:
                score += combination[0].get_distance_to(combination[1])
            return score

        return min(all_combinations, key=key_func)

    def get_defensive_positions(self):
        my_heroes = self.get_my_heroes()
        defensive_positions = [Point(3535, 3535), Point(1500, 4850), Point(4850, 1500)]
        defensive_positions_relative_to_base = list(
            map(lambda location: abs(location - self.my_base_location), defensive_positions))

        return self.get_optimal_combination_heroes_to_points(my_heroes, defensive_positions_relative_to_base)

    def assign_heroes_to_monsters(self, monsters_near_heroes_dict: dict) -> dict:
        all_combinations = itertools.product(
            *monsters_near_heroes_dict.values())  # all possible combinations of monsters
        legal_combinations = []
        for potential_combination in all_combinations:
            hero_id_to_potential_monster = dict()
            for hero_id, monster in enumerate(potential_combination):
                hero_id_to_potential_monster[hero_id] = monster
            used_monsters_cache = []
            for hero_id, monster in hero_id_to_potential_monster.items():
                if monster not in used_monsters_cache:
                    used_monsters_cache.append(monster)
                else:
                    hero_id_to_potential_monster[hero_id] = None
            legal_combinations.append(hero_id_to_potential_monster)

        # returns the best option based on the highest amount of monsters assigned to heroes
        # im sorry
        spells_to_cast_in_a_turn = min(self.my_mana // SPELL_COST, self.heroes_per_player)  # Rounded to the closest int
        legal_combinations = filter(lambda combination: len(
            [val for val in combination.values() if val is not None]) <= spells_to_cast_in_a_turn, legal_combinations)
        return max(legal_combinations, key=lambda lambda_d: len([val for val in lambda_d.values() if val is not None]),
                   default={})

    def get_monsters_near_heroes_dict(self, spell_range):
        return_dict = dict()
        for hero in self.get_my_heroes():
            return_dict[hero.hero_id] = [monster.id for monster in
                                         hero.get_monsters_in_spell_range(self.get_dangerous_monsters((TARGETING_ME, ROAMING_TOWARDS_ME, CLUELESS)), spell_range)]

        return return_dict

    def get_entity_from_id(self, entity_id: int) -> ['Hero', 'Monster', None]:
        return next(filter(lambda entity: entity.hero_id == entity_id, self.get_my_heroes() + self.monsters), None)

    def get_dangerous_monsters(self, target: tuple):
        return list(filter(
            lambda monster: not monster.is_controlled and monster.target in target,
            self.monsters))


class Hero:
    def __init__(self, hero_id, team, location, shield_life, is_controlled):
        self.team = team
        self.hero_id = hero_id
        self.location = location
        self.shield_life = shield_life
        self.is_controlled = is_controlled

    def __repr__(self):
        return "\nHERO: " + "\n\t".join(
            map(lambda attribute: f"{attribute[0]} = {attribute[1]}", self.__dict__.items()))

    def get_distance_to(self, other_location: Point):
        return self.location.get_distance_to(other_location)

    def get_monster_value(self, monster, my_base_location: Point) -> int:
        """
        Higher value -> more dangerous
        :param monster: Monster Object
        :param my_base_location: Point
        :return: int
        """
        base_proximity_factor = monster.get_distance_to(my_base_location) * -1
        hero_proximity_factor = self.get_distance_to(monster.location) * -1
        is_targeting_factor = (monster.target == TARGETING_ME) * 1000

        return base_proximity_factor + hero_proximity_factor + is_targeting_factor

    def get_most_dangerous_monster(self, monsters: list['Monster'], my_base_location: Point) -> 'Monster':

        return max(monsters, key=lambda monster: self.get_monster_value(monster, my_base_location), default=None)

    def get_monsters_in_spell_range(self, monsters: list['Monster'], spell_range: int) -> list['Monster']:
        return_value = []
        for monster in monsters:
            if monster.get_distance_to(self.location) <= spell_range:
                return_value.append(monster)
        return return_value


@dataclass
class Monster:
    id: int
    location: Point
    shield_life: int
    is_controlled: bool
    hp: int
    trajectory: Point
    target: tuple[int, int]

    def __repr__(self):
        return "\nMONSTER: " + "\n\t".join(
            map(lambda attribute: f"{attribute[0]} = {attribute[1]}", self.__dict__.items()))

    def get_distance_to(self, other_location: Point):
        return self.location.get_distance_to(other_location)

    def is_in_base(self):
        return self.target == TARGETING_ME


def debug(*args, **kwargs):
    if DEBUG:
        sys.stderr.write(f'{args=} {kwargs=}\n')


def build_game_from_input():
    base_x, base_y = [int(i) for i in input().split()]
    heroes_per_player = int(input())

    return Game(Point(base_x, base_y), heroes_per_player)


def build_entity_from_input():
    _id, team, x, y, shield_life, is_controlled, health, vx, vy, near_base, threat_for = [int(j) for j in
                                                                                          input().split()]
    location = Point(x, y)
    trajectory = Point(vx, vy)
    target = (near_base, threat_for)

    if team == MONSTER_TEAM:
        return Monster(_id, location, shield_life, is_controlled, health, trajectory, target)

    return Hero(_id, team, location, shield_life, is_controlled)


game = build_game_from_input()

# game loop
while True:
    game.update_turn_data()

    debug(game)

    game.make_turn()
