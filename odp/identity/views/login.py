from flask import Blueprint, render_template, redirect, url_for, request

from odp.identity import hydra_admin
from odp.identity.forms import LoginForm, VerifyEmailForm, ForgotPasswordForm, GoogleForm
from odp.identity.views import encode_token, decode_token, hydra_error_page
from odp.identity.views.account import send_verification_email, send_password_reset_email
from odp.lib import exceptions as x
from odp.lib.users import validate_auto_login, validate_user_login, validate_forgot_password

bp = Blueprint('login', __name__)


@bp.route('/', methods=('GET', 'POST'))
def login():
    """User login view.

    The token ensures that we can only access this view in the context
    of the Hydra login workflow.
    """
    token = request.args.get('token')
    try:
        login_request, challenge, params = decode_token(token, 'login')

        user_id = None
        error = None
        form = LoginForm()
        gform = GoogleForm()

        if request.method == 'GET':
            authenticated = login_request['skip']  # indicates whether the user is already authenticated with Hydra

            # if already authenticated, we'll wind up with either a user_id or an error
            if authenticated:
                user_id = login_request['subject']
                try:
                    validate_auto_login(user_id)
                except x.ODPIdentityError as e:
                    # any validation error => reject login
                    user_id = None
                    error = e

            # if not authenticated, we'll display the login form

        else:  # POST
            if form.validate():
                email = form.email.data
                password = form.password.data
                try:
                    user_id = validate_user_login(email, password)

                except x.ODPUserNotFound:
                    form.email.errors.append("The email address is not associated with any user account.")

                except x.ODPIncorrectPassword:
                    form.email.errors.append("The email address and password do not match.")

                except x.ODPEmailNotVerified:
                    # the login is completed via email verification
                    send_verification_email(email, challenge)
                    verify_token = encode_token(challenge, 'login.verify', email=email)
                    return redirect(url_for('.verify', token=verify_token))

                except x.ODPIdentityError as e:
                    # any other validation error (e.g. account locked/disabled) => reject login
                    error = e

        if user_id:
            redirect_to = hydra_admin.accept_login_request(challenge, user_id)
        elif error:
            redirect_to = hydra_admin.reject_login_request(challenge, error.error_code, error.error_description)
        else:
            return render_template('login.html', form=form, gform=gform, token=token)

        return redirect(redirect_to)

    except x.HydraAdminError as e:
        return hydra_error_page(e)


@bp.route('/verify', methods=('GET', 'POST'))
def verify():
    """View for sending a verification email.

    The token ensures that we can only get here from the user login view.
    """
    token = request.args.get('token')
    try:
        login_request, challenge, params = decode_token(token, 'login.verify')

        form = VerifyEmailForm()
        email = params.get('email')

        if request.method == 'POST':
            send_verification_email(email, challenge)

        return render_template('login_verify.html', form=form, token=token)

    except x.HydraAdminError as e:
        return hydra_error_page(e)


@bp.route('/forgot-password', methods=('GET', 'POST'))
def forgot_password():
    """View for sending a password reset email.

    The token ensures that we can only access this view in the context
    of the Hydra login workflow.
    """
    token = request.args.get('token')
    try:
        login_request, challenge, params = decode_token(token, 'login')

        form = ForgotPasswordForm()

        if request.method == 'POST':
            if form.validate():
                email = form.email.data
                try:
                    user_id = validate_forgot_password(email)
                    send_password_reset_email(email, challenge)

                except x.ODPUserNotFound:
                    form.email.errors.append("The email address is not associated with any user account.")

                except x.ODPIdentityError as e:
                    # any other validation error => reject login
                    redirect_to = hydra_admin.reject_login_request(challenge, e.error_code, e.error_description)
                    return redirect(redirect_to)

        return render_template('forgot_password.html', form=form, token=token)

    except x.HydraAdminError as e:
        return hydra_error_page(e)
