import argon2
from argon2.exceptions import VerifyMismatchError

from odpaccounts.db import session as db_session
from odpaccounts.models.privilege import Privilege
from odpaccounts.models.scope import Scope
from odpaccounts.models.user import User

from ..lib import exceptions as x

ph = argon2.PasswordHasher()


def validate_user_login(email, password):
    """
    Validate the credentials supplied by a user via the login form, returning the user object
    on success. An ``ODPLoginError`` is raised if the login cannot be permitted for any reason.

    :param email: the input email address
    :param password: the input plain-text password
    :return: a User object

    :raises ODPUserNotFound: if the email address is not associated with any user account
    :raises ODPAccountLocked: if the user account has been temporarily locked
    :raises ODPIncorrectPassword: if the password is incorrect
    :raises ODPAccountDisabled: if the user account has been deactivated
    :raises ODPEmailNotConfirmed: if the email address has not yet been verified
    """
    user = db_session.query(User).filter_by(email=email).first()
    if not user:
        raise x.ODPUserNotFound

    # first check whether the account is currently locked and should still be locked, unlocking it if necessary
    if is_account_locked(user):
        raise x.ODPAccountLocked

    # check the password before checking further account properties, to minimize the amount of knowledge
    # a potential attacker can gain about an account
    try:
        ph.verify(user.password, password)

        # if argon2_cffi's password hashing defaults have changed, we rehash the user's password
        if ph.check_needs_rehash(user.password):
            user.password = ph.hash(password)
            db_session.add(user)
            db_session.commit()

    except VerifyMismatchError:
        if lock_account(user):
            raise x.ODPAccountLocked
        raise x.ODPIncorrectPassword

    if not user.active:
        raise x.ODPAccountDisabled

    if not user.confirmed_at:
        raise x.ODPEmailNotConfirmed

    return user


def validate_auto_login(user_id):
    """
    Validate a login request for which Hydra has indicated that the user is already authenticated,
    returning the user object on success. An ``ODPLoginError`` is raised if the login cannot be
    permitted for any reason.

    :param user_id: the user id
    :return: a User object

    :raises ODPUserNotFound: if the user account associated with this id has been deleted
    :raises ODPAccountLocked: if the user account has been temporarily locked
    :raises ODPAccountDisabled: if the user account has been deactivated
    :raises ODPEmailNotConfirmed: if the user changed their email address since their last login,
        but have not yet verified it
    """
    user = db_session.query(User).get(user_id)
    if not user:
        raise x.ODPUserNotFound

    if is_account_locked(user):
        raise x.ODPAccountLocked

    if not user.active:
        raise x.ODPAccountDisabled

    if not user.confirmed_at:
        raise x.ODPEmailNotConfirmed

    return user


def is_account_locked(user):
    # todo...
    return False


def lock_account(user):
    # todo...
    return False


def validate_user_registration(email, password):
    """
    Validate the credentials supplied by a new user. An ``ODPUserRegistrationError``
    is raised if the registration cannot be permitted for any reason.

    :param email: the input email address
    :param password: the input plain-text password

    :raises ODPUserAlreadyExists: if the email address is already associated with a user account
    :raises ODPPasswordComplexityError: if the password does not meet the minimum complexity requirements
    """
    user = db_session.query(User).filter_by(email=email).first()
    if user:
        raise x.ODPUserAlreadyExists

    if not check_password_complexity(password):
        raise x.ODPPasswordComplexityError


def create_user_account(email, password):
    """
    Create a new user account with the specified credentials. The password is hashed
    using the Argon2id algorithm.

    :param email: the input email address
    :param password: the input plain-text password
    :return: a User object
    """
    import datetime
    user = User(
        email=email,
        password=ph.hash(password),
        superuser=False,
        active=True,
        confirmed_at = datetime.datetime.now()  # todo: remove once we've implemented email confirmation
    )
    db_session.add(user)
    db_session.commit()

    return user


def check_password_complexity(password):
    """
    Check that a password meets the minimum complexity requirements, returning True if the
    requirements are met, False otherwise.

    :param password: the input plain-text password
    :return: boolean
    """
    # todo...
    return len(password) >= 4


def id_token_data(user):
    """
    Construct a dict of items to put in an ID token for this user.

    :param user: a User instance
    :return: dict
    """
    return {'email': user.email}


def access_token_data(user, scopes):
    """
    Construct a dict of items to put in an access token for this user.
    This is structured as follows::
        {
            'superuser': True/False,
            'privileges': [{
                'institution': institution code,
                'institution_name': institution name,
                'role': role code,
                'role_name': role name,
                'scope': scope code,
            }, ...]
        }

    Privileges are filtered to include only those applicable to the requested scopes.
    If the user is a superuser, privileges will be an empty list, since a superuser
    can do anything anyway.

    :param user: a User instance
    :param scopes: list of scopes being requested for the token
    :return: dict
    """
    access_info = {
        'superuser': user.superuser,
        'privileges': [],
    }
    if not user.superuser:
        privileges = db_session.query(Privilege).filter_by(user_id=user.id) \
            .join(Scope, Privilege.scope_id == Scope.id).filter(Scope.code.in_(scopes)) \
            .all()
        for privilege in privileges:
            access_info['privileges'] += [{
                'institution': privilege.institution.code,
                'institution_name': privilege.institution.name,
                'role': privilege.role.code,
                'role_name': privilege.role.name,
                'scope': privilege.scope.code,
            }]
    return access_info
