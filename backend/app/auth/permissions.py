from enum import StrEnum

from app.models.users import Role


class Perm(StrEnum):
    VIEW = "view"  # смотреть, искать, выгружать
    OPERATE = "operate"  # статусы, перемещения, ремонты, узлы
    EDIT = "edit"  # банкоматы, сертификаты, договоры
    MANAGE_REFERENCE = "manage_reference"  # справочники, модели, импорт
    MANAGE_USERS = "manage_users"
    SUPERADMIN = "superadmin"  # удаление, журнал изменений, назначение суперадминов


ROLE_PERMS: dict[Role, frozenset[Perm]] = {
    Role.VIEWER: frozenset({Perm.VIEW}),
    Role.OPERATOR: frozenset({Perm.VIEW, Perm.OPERATE}),
    Role.ADMIN: frozenset({Perm.VIEW, Perm.OPERATE, Perm.EDIT, Perm.MANAGE_REFERENCE, Perm.MANAGE_USERS}),
    Role.SUPERADMIN: frozenset(Perm),
}


def perms_of(role: str) -> frozenset[Perm]:
    return ROLE_PERMS[Role(role)]
