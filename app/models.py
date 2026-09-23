from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Boolean, Date, DateTime, Text, ForeignKey, Table
)
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.database import Base


# Many-to-Many association tables for Management relations
# "в Управление может входить несколько округов, в управление может входить несколько участков"
management_districts = Table(
    'management_districts',
    Base.metadata,
    Column('management_id', Integer, ForeignKey('managements.id', ondelete='CASCADE'), primary_key=True),
    Column('district_id', Integer, ForeignKey('districts.id', ondelete='CASCADE'), primary_key=True)
)

management_plots = Table(
    'management_plots',
    Base.metadata,
    Column('management_id', Integer, ForeignKey('managements.id', ondelete='CASCADE'), primary_key=True),
    Column('plot_id', Integer, ForeignKey('plots.id', ondelete='CASCADE'), primary_key=True)
)


class User(Base, UserMixin):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    full_name = Column(String(128), nullable=False)
    role = Column(String(32), default='registrator', nullable=False)  # 'superadmin' or 'registrator'
    is_builtin = Column(Boolean, default=False, nullable=False)  # Built-in superadmin from .env
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    # Relationships to appeals
    created_appeals = relationship('Appeal', foreign_keys='Appeal.created_by_id', back_populates='created_by')
    closed_appeals = relationship('Appeal', foreign_keys='Appeal.closed_by_id', back_populates='closed_by')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_superadmin(self):
        return self.role == 'superadmin'

    @property
    def is_registrator(self):
        return self.role == 'registrator' or self.role == 'superadmin'

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


# 1. Источник поступления
class Source(Base):
    __tablename__ = 'sources'

    id = Column(Integer, primary_key=True)
    name = Column(String(512), unique=True, nullable=False)
    code = Column(String(64), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    appeals = relationship('Appeal', back_populates='source')

    def __repr__(self):
        return f'<Source {self.name}>'


# 2. Округ
class District(Base):
    __tablename__ = 'districts'

    id = Column(Integer, primary_key=True)
    name = Column(String(512), unique=True, nullable=False)
    code = Column(String(64), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    managements = relationship(
        'Management',
        secondary=management_districts,
        back_populates='districts'
    )
    appeals = relationship('Appeal', back_populates='district')

    def __repr__(self):
        return f'<District {self.name}>'


# 3. Управление
class Management(Base):
    __tablename__ = 'managements'

    id = Column(Integer, primary_key=True)
    name = Column(String(512), unique=True, nullable=False)
    code = Column(String(64), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # В управление может входить несколько округов
    districts = relationship(
        'District',
        secondary=management_districts,
        back_populates='managements'
    )
    # В управление может входить несколько участков
    plots = relationship(
        'Plot',
        secondary=management_plots,
        back_populates='managements'
    )
    appeals = relationship('Appeal', back_populates='management')

    def __repr__(self):
        return f'<Management {self.name}>'


# 4. Участок
class Plot(Base):
    __tablename__ = 'plots'

    id = Column(Integer, primary_key=True)
    name = Column(String(512), unique=True, nullable=False)
    code = Column(String(64), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    managements = relationship(
        'Management',
        secondary=management_plots,
        back_populates='plots'
    )
    appeals = relationship('Appeal', back_populates='plot')

    def __repr__(self):
        return f'<Plot {self.name}>'


# 5. Тип обращения
class AppealType(Base):
    __tablename__ = 'appeal_types'

    id = Column(Integer, primary_key=True)
    name = Column(String(512), unique=True, nullable=False)
    code = Column(String(64), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    appeals = relationship('Appeal', back_populates='appeal_type')

    def __repr__(self):
        return f'<AppealType {self.name}>'


# 6. Тематика обращения
class Topic(Base):
    __tablename__ = 'topics'

    id = Column(Integer, primary_key=True)
    name = Column(String(512), unique=True, nullable=False)
    code = Column(String(64), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    appeals = relationship('Appeal', back_populates='topic')

    def __repr__(self):
        return f'<Topic {self.name}>'


# 7. Результат рассмотрения
class Result(Base):
    __tablename__ = 'results'

    id = Column(Integer, primary_key=True)
    name = Column(String(512), unique=True, nullable=False)
    code = Column(String(64), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    appeals = relationship('Appeal', back_populates='result')

    def __repr__(self):
        return f'<Result {self.name}>'


# Main Model: Обращение граждан
class Appeal(Base):
    __tablename__ = 'appeals'

    id = Column(Integer, primary_key=True)
    number = Column(String(100), nullable=False, index=True)  # № обращения из внешней системы
    reg_date = Column(Date, nullable=False, index=True)  # Дата регистрации (DD.MM.YYYY, <= today)
    status = Column(String(50), default='В работе', nullable=False, index=True)  # 'В работе', 'Закрыто'

    # Foreign Keys to Reference Books
    source_id = Column(Integer, ForeignKey('sources.id'), nullable=False)
    district_id = Column(Integer, ForeignKey('districts.id'), nullable=False)
    management_id = Column(Integer, ForeignKey('managements.id'), nullable=True)
    plot_id = Column(Integer, ForeignKey('plots.id'), nullable=True)

    # Static Choice Fields
    applicant_gender = Column(String(20), nullable=True)  # 'мужской', 'женский'
    appeal_type_id = Column(Integer, ForeignKey('appeal_types.id'), nullable=False)
    topic_id = Column(Integer, ForeignKey('topics.id'), nullable=False)
    validity = Column(String(50), nullable=True)  # 'обоснован', 'не обоснован'
    recurrence = Column(String(50), nullable=True)  # 'Первичное', 'Повторное', 'Многократное'
    result_id = Column(Integer, ForeignKey('results.id'), nullable=True)

    # Deadline & Serviced Flag
    deadline_date = Column(Date, nullable=True, index=True)  # Контрольные сроки
    not_serviced = Column(Boolean, default=False, nullable=False)  # Не состоит на обслуживании

    # Details & Comments
    comment = Column(Text, nullable=True)

    # Metadata: Who added and when
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    created_by_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    # Closing metadata: When closed and by whom
    closed_at = Column(DateTime, nullable=True)
    closed_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    # Relationships
    source = relationship('Source', back_populates='appeals')
    district = relationship('District', back_populates='appeals')
    management = relationship('Management', back_populates='appeals')
    plot = relationship('Plot', back_populates='appeals')
    appeal_type = relationship('AppealType', back_populates='appeals')
    topic = relationship('Topic', back_populates='appeals')
    result = relationship('Result', back_populates='appeals')
    created_by = relationship('User', foreign_keys=[created_by_id], back_populates='created_appeals')
    closed_by = relationship('User', foreign_keys=[closed_by_id], back_populates='closed_appeals')

    @property
    def is_closed(self):
        return self.status == 'Закрыто'

    @property
    def is_serviced(self):
        """Состоит на обслуживании: True если флаг 'Не состоит на обслуживании' равен False."""
        return not self.not_serviced

    @property
    def days_until_deadline(self):
        """Количество дней до ответа от текущей даты."""
        if not self.deadline_date:
            return None
        today = date.today()
        return (self.deadline_date - today).days

    @property
    def reg_date_european(self):
        """Европейский стандарт отображения даты: DD.MM.YYYY"""
        if self.reg_date:
            return self.reg_date.strftime('%d.%m.%Y')
        return ''

    @property
    def deadline_date_european(self):
        """Европейский стандарт отображения даты контрольного срока: DD.MM.YYYY"""
        if self.deadline_date:
            return self.deadline_date.strftime('%d.%m.%Y')
        return ''

    @property
    def closed_at_formatted(self):
        """Дата и время закрытия: DD.MM.YYYY HH:MM"""
        if self.closed_at:
            return self.closed_at.strftime('%d.%m.%Y %H:%M')
        return ''

    @property
    def created_at_formatted(self):
        """Дата и время добавления: DD.MM.YYYY HH:MM"""
        if self.created_at:
            return self.created_at.strftime('%d.%m.%Y %H:%M')
        return ''

    def __repr__(self):
        return f'<Appeal {self.number} ({self.status})>'
