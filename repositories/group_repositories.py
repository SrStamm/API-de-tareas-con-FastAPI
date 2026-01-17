from models.exceptions import DatabaseError
from models.schemas import CreateGroup, ReadGroup, UpdateGroup
from models.db_models import Group, group_user, Group_Role, User
from db.database import Session, SQLAlchemyError, select, selectinload
from typing import List, Dict


class GroupRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_group_by_id(self, group_id: int) -> ReadGroup:
        try:
            stmt = (
                select(Group)
                .options(selectinload(Group.users))
                .where(Group.group_id == group_id)
            )
            return self.session.exec(stmt).first()
        except SQLAlchemyError as e:
            raise DatabaseError(e, "GroupRepository.get_group_by_id")
        except Exception:
            raise

    def get_all_groups(self, limit: int, skip: int) -> List[Dict]:
        try:
            stmt = (
                select(Group)
                .options(selectinload(Group.users))
                .order_by(Group.group_id)
                .limit(limit)
                .offset(skip)
            )
            return self.session.exec(stmt).all()
        except SQLAlchemyError as e:
            raise DatabaseError(e, "get_all_groups")

    def get_groups_for_user(self, user_id: int, limit: int, skip: int):
        try:
            stmt = (
                select(Group)
                .join(group_user, group_user.group_id == Group.group_id)
                .where(group_user.user_id == user_id)
                .order_by(Group.group_id)
                .limit(limit)
                .offset(skip)
            )

            return self.session.exec(stmt).all()
        except SQLAlchemyError as e:
            raise DatabaseError(e, "get_groups_for_user")

    def get_users_for_group(self, group_id: int):
        try:
            stmt = (
                select(User.username, User.user_id, group_user.role)
                .join(group_user, group_user.user_id == User.user_id)
                .where(group_user.group_id == group_id)
            )

            return self.session.exec(stmt).all()
        except SQLAlchemyError as e:
            raise DatabaseError(e, "get_users_for_group")

    def get_role_for_user_in_group(self, group_id: int, user_id: int):
        try:
            stmt = select(group_user).where(
                group_user.user_id == user_id, group_user.group_id == group_id
            )

            return self.session.exec(stmt).first()
        except SQLAlchemyError as e:
            raise DatabaseError(e, "get_role_for_user_in_group")

    def create(self, group_data: CreateGroup, user_id: int) -> Group:
        try:
            # Create a group
            new_group = Group(**group_data.model_dump())
            self.session.add(new_group)
            self.session.flush()

            # Create a relation with user
            user_in_group = group_user(
                group_id=new_group.group_id, user_id=user_id, role=Group_Role.ADMIN
            )
            self.session.add(user_in_group)

            self.session.commit()
            self.session.refresh(new_group, attribute_names=["users"])
            return new_group

        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(e, "create")

        except Exception:
            self.session.rollback()
            raise

    def update(self, actual_group: Group, update_group: UpdateGroup):
        try:
            if update_group.name and actual_group.name != update_group.name:
                actual_group.name = update_group.name

            if (
                update_group.description
                and actual_group.description != update_group.description
            ):
                actual_group.description = update_group.description

            self.session.commit()
            self.session.refresh(actual_group, attribute_names=["users"])
            return actual_group

        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(e, "update")

        except Exception:
            self.session.rollback()
            raise

    def delete(self, group: Group):
        try:
            self.session.delete(group)
            self.session.commit()
            return

        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(e, "delete")

        except Exception:
            self.session.rollback()
            raise

    def append_user(self, group_id: int, user: User):
        try:
            group = self.get_group_by_id(group_id)
            group.users.append(user)
            self.session.commit()
            return

        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(e, "append_user")

        except Exception:
            self.session.rollback()
            raise

    def delete_user(self, group_id: int, user: User):
        try:
            group = self.get_group_by_id(group_id)
            group.users.remove(user)
            self.session.commit()
            return

        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(e, "delete_user")

        except Exception:
            self.session.rollback()
            raise

    def update_role(self, user_id: int, role: Group_Role):
        try:
            stmt = (
                select(group_user)
                .join(Group, group_user.group_id == Group.group_id)
                .where(group_user.user_id == user_id)
            )
            user = self.session.exec(stmt).first()

            user.role == role
            self.session.commit()

        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(e, "update_role")

        except Exception:
            self.session.rollback()
            raise
