from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, InputRequired, Length, ValidationError
from wtforms import StringField, SubmitField, TextAreaField, BooleanField

from flask_login import current_user

from app.features.bundle.bundle_core import bundle_name_taken

class AddNewBundleForm(FlaskForm):
    """Form to create a new bundle."""
    
    name = StringField('Bundle Name', filters=[lambda v: v.strip() if isinstance(v, str) else v], validators=[
        DataRequired(message="Bundle name is required"),
        Length(max=255, message="Bundle name must be less than 255 characters")
    ])
    
    description = TextAreaField('Description', validators=[
        InputRequired(message="Bundle description is required")
    ])
    
    # Matches your 'access' field in the DB
    public = BooleanField('Public', default=True) 
    
    submit = SubmitField('Create Bundle')

    def validate_name(self, field):
        # A name is unique per user — two users may each have a bundle "Ransomware"
        if bundle_name_taken(field.data, current_user.id):
            raise ValidationError('You already have a bundle with this name.')

class EditBundleForm(FlaskForm):
    """Form to edit a bundle."""

    name = StringField('Bundle Name', filters=[lambda v: v.strip() if isinstance(v, str) else v], validators=[
        DataRequired(message="Bundle name is required"),
        Length(max=255, message="Bundle name must be less than 255 characters")
    ])
    description = TextAreaField('Description', validators=[InputRequired(message="Bundle description is required")])
    public = BooleanField('Public', default=True)

    submit = SubmitField('Save')

    def __init__(self, bundle_id=None, owner_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bundle_id = bundle_id
        self.owner_id = owner_id

    def validate_name(self, field):
        # Unique among the bundle owner's bundles (an admin editing it included)
        if bundle_name_taken(field.data, self.owner_id, exclude_id=self.bundle_id):
            raise ValidationError('The owner already has a bundle with this name.')