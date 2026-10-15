"""Blog posts and what they reference.
"""
from app import db
import datetime


##############
#    Blog    #
##############

class BlogPost(db.Model):
    __tablename__ = 'blog_post'
    id           = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid         = db.Column(db.String(36), unique=True, nullable=False, index=True)
    slug         = db.Column(db.String(255), unique=True, nullable=False, index=True)
    title        = db.Column(db.String(255), nullable=False)
    excerpt      = db.Column(db.Text, nullable=True)
    content      = db.Column(db.Text, nullable=False, default='')
    user_id      = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)
    is_public    = db.Column(db.Boolean, nullable=False, default=False, index=True)
    is_draft     = db.Column(db.Boolean, nullable=False, default=True,  index=True)
    share_key    = db.Column(db.String(64), nullable=True, index=True)
    view_count   = db.Column(db.Integer, nullable=False, default=0)
    cve_ids          = db.Column(db.JSON, nullable=True)
    cover_image_url  = db.Column(db.String(500), nullable=True)
    external_links   = db.Column(db.JSON, nullable=True)
    # A Pivograph map attached to the post (github.com/ecrou-exact/project-graph
    # document format), edited in the post editor, shown and downloadable on the
    # post page. Validated by blog_core.clean_graph.
    graph            = db.Column(db.JSON, nullable=True)
    # How readers see it: 'full' (Pivograph with its panels) or 'simple' (just the graph).
    graph_view       = db.Column(db.String(16), nullable=False, default='full', server_default='full')
    created_at   = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at   = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    published_at = db.Column(db.DateTime, nullable=True)

    author  = db.relationship('User', foreign_keys=[user_id], lazy='joined')
    tags    = db.relationship('BlogPostTagAssociation', backref='post', cascade='all, delete-orphan', lazy='joined')
    rules   = db.relationship('BlogPostRuleAssociation', backref='post', cascade='all, delete-orphan', order_by='BlogPostRuleAssociation.position')
    bundles = db.relationship('BlogPostBundleAssociation', backref='post', cascade='all, delete-orphan', order_by='BlogPostBundleAssociation.position')
    files   = db.relationship('BlogPostFile', backref='post', cascade='all, delete-orphan', order_by='BlogPostFile.created_at')
    attacks = db.relationship('BlogPostAttackAssociation', backref='post', cascade='all, delete-orphan')

    def to_json(self):
        return {
            'id':            self.id,
            'uuid':          self.uuid,
            'slug':          self.slug,
            'title':         self.title,
            'excerpt':       self.excerpt,
            'content':       self.content,
            'user_id':       self.user_id,
            'is_public':     self.is_public,
            'is_draft':      self.is_draft,
            'has_share_key':    bool(self.share_key),
            'cover_image_url':  self.cover_image_url,
            'external_links':   self.external_links or [],
            'has_graph':        self.graph is not None,
            'graph_view':       self.graph_view or 'full',
            'files':            [f.to_json() for f in self.files],
            'view_count':    self.view_count,
            'cve_ids':       self.cve_ids or [],
            'created_at':    self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
            'updated_at':    self.updated_at.strftime('%Y-%m-%d %H:%M') if self.updated_at else None,
            'published_at':  self.published_at.strftime('%Y-%m-%d') if self.published_at else None,
            'author_name':   ((self.author.first_name or '') + ' ' + (self.author.last_name or '')).strip() if self.author else 'Unknown',
            'author_username': self.author.get_username() if self.author else None,
            'author_id':     self.user_id,
            'author_avatar': self.author.get_avatar_url() if self.author else None,
            'tag_names':     [a.tag.name for a in self.tags if a.tag],
            'tags':          [a.tag.to_json() for a in self.tags if a.tag],
            'technique_ids': [a.technique_id for a in self.attacks],
            'rule_ids':      [r.rule_id for r in self.rules],
            'bundle_ids':    [b.bundle_id for b in self.bundles],
        }


class BlogPostTagAssociation(db.Model):
    __tablename__ = 'blog_post_tag'
    id      = db.Column(db.Integer, primary_key=True, autoincrement=True)
    post_id = db.Column(db.Integer, db.ForeignKey('blog_post.id', ondelete='CASCADE'), nullable=False, index=True)
    tag_id  = db.Column(db.Integer, db.ForeignKey('tag.id', ondelete='CASCADE'), nullable=False)
    tag     = db.relationship('Tag', lazy='joined')


class BlogPostRuleAssociation(db.Model):
    __tablename__ = 'blog_post_rule'
    id       = db.Column(db.Integer, primary_key=True, autoincrement=True)
    post_id  = db.Column(db.Integer, db.ForeignKey('blog_post.id', ondelete='CASCADE'), nullable=False, index=True)
    rule_id  = db.Column(db.Integer, db.ForeignKey('rule.id', ondelete='CASCADE'), nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)


class BlogPostBundleAssociation(db.Model):
    __tablename__ = 'blog_post_bundle'
    id        = db.Column(db.Integer, primary_key=True, autoincrement=True)
    post_id   = db.Column(db.Integer, db.ForeignKey('blog_post.id', ondelete='CASCADE'), nullable=False, index=True)
    bundle_id = db.Column(db.Integer, db.ForeignKey('bundle.id', ondelete='CASCADE'), nullable=False)
    position  = db.Column(db.Integer, nullable=False, default=0)


class BlogPostAttackAssociation(db.Model):
    __tablename__ = 'blog_post_attack'
    id           = db.Column(db.Integer, primary_key=True, autoincrement=True)
    post_id      = db.Column(db.Integer, db.ForeignKey('blog_post.id', ondelete='CASCADE'), nullable=False, index=True)
    technique_id = db.Column(db.String(16), nullable=False)


class BlogPostFile(db.Model):
    __tablename__ = 'blog_post_file'
    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid          = db.Column(db.String(36), unique=True, nullable=False, index=True)
    post_id       = db.Column(db.Integer, db.ForeignKey('blog_post.id', ondelete='CASCADE'), nullable=False, index=True)
    original_name = db.Column(db.String(255), nullable=False)
    stored_name   = db.Column(db.String(255), nullable=False)
    mime_type     = db.Column(db.String(128), nullable=False)
    size_bytes    = db.Column(db.Integer, nullable=False)
    uploaded_by   = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    created_at    = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)

    def to_json(self):
        return {
            'id':            self.id,
            'uuid':          self.uuid,
            'original_name': self.original_name,
            'mime_type':     self.mime_type,
            'size_bytes':    self.size_bytes,
            'created_at':    self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
            'download_url':  f'/blog/admin/file/{self.uuid}',
        }
