import sys
import math
from dataclasses import dataclass
import numpy

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


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.array = numpy.array([x, y])

    def __repr__(self):
        return str((self.x, self.y))

    def get_distance_to(self, other):
        return numpy.linalg.norm(self.array - other.array)

    def __sub__(self, other):
        return Point(self.x - other.x, self.y - other.y)

    def __abs__(self):
        return Point(abs(self.x), abs(self.y))


TOP_LEFT = Point(0, 0)
BOTTOM_RIGHT = Point(17630, 9000)


class Game:
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

    def make_turn(self):
        if self.monsters:
            for my_hero in self.get_my_heroes():
                scary_monster = my_hero.get_most_dangerous_monster(self.monsters, self.my_base_location)
                debug(f"Scary monster for Hero {my_hero.hero_id}: {scary_monster}")
                my_hero.move(scary_monster.location)

        else:
            defensive_positions = self.get_defensive_positions()
            for my_hero in self.get_my_heroes():
                my_hero.move(defensive_positions[my_hero.hero_id])

    def get_targeting_monsters(self):
        return filter(lambda monster: monster.target == TARGETING_ME, self.monsters)

    def get_my_heroes(self):
        return sorted(filter(lambda hero: hero.team == MY_TEAM, self.heroes), key=lambda hero: hero.hero_id)

    def get_defensive_positions(self):
        defensive_positions = [Point(3535, 3535), Point(1500, 4850), Point(4850, 1500)]
        return list(map(lambda location: abs(location - self.my_base_location), defensive_positions))


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

    def do(self, command):
        print(command)  # + f" {self.hero_id}: " + command)

    def get_distance_to(self, other_location: Point):
        return self.location.get_distance_to(other_location)

    def get_monster_value(self, monster, my_base_location: Point):
        base_proximity_factor = monster.get_distance_to(my_base_location) * -1
        hero_proximity_factor = self.get_distance_to(monster.location) * -1
        is_targeting_factor = (monster.target == TARGETING_ME) * 1000

        return base_proximity_factor + hero_proximity_factor + is_targeting_factor

    def move(self, target: Point):
        self.do(f"MOVE {target.x} {target.y}")

    def wait(self):
        self.do("WAIT")

    def get_most_dangerous_monster(self, monsters, my_base_location):
        return max(monsters, key=lambda monster: self.get_monster_value(monster, my_base_location))


@dataclass
class Monster:
    id: int
    location: Point
    shield_life: int
    is_controlled: bool
    hp: int
    trajectory: Point
    target: (int, int)

    def __repr__(self):
        return "\nMONSTER: " + "\n\t".join(
            map(lambda attribute: f"{attribute[0]} = {attribute[1]}", self.__dict__.items()))

    def get_distance_to(self, other_location: Point):
        return self.location.get_distance_to(other_location)


def debug(s):
    sys.stderr.write(f'{s}\n')


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
