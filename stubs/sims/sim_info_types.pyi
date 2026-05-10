import enum

class Gender(enum.IntEnum):
    MALE = 4096
    FEMALE = 8192

class Age(enum.IntEnum):
    BABY = 1
    TODDLER = 2
    CHILD = 4
    TEEN = 8
    YOUNGADULT = 16
    ADULT = 32
    ELDER = 64
    INFANT = 128
