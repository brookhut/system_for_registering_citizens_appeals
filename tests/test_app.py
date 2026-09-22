import unittest
from datetime import date, datetime, timedelta
from app import create_app
from app.config import Config
from app.database import db_session, init_db
from app.models import (
    User, Appeal, Source, District, Management, Plot, AppealType, Topic, Result,
    management_districts, management_plots
)
from app.utils import parse_date, format_date_eur
from run import is_port_available, find_available_port


class AppealsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        with self.app.app_context():
            init_db()
            # Create a test registrator for tests
            test_reg = db_session.query(User).filter_by(username='test_registrator').first()
            if not test_reg:
                test_reg = User(
                    username='test_registrator',
                    full_name='Тестовый Регистратор',
                    role='registrator',
                    is_builtin=False,
                    is_active=True
                )
                test_reg.set_password('TestPass2026!')
                db_session.add(test_reg)

            # Create test dictionary entries for testing
            self.test_source = db_session.query(Source).filter_by(name='Тест Источник').first()
            if not self.test_source:
                self.test_source = Source(name='Тест Источник', code='ТИ', is_active=True)
                db_session.add(self.test_source)

            self.test_district = db_session.query(District).filter_by(name='Тест Округ').first()
            if not self.test_district:
                self.test_district = District(name='Тест Округ', code='ТО', is_active=True)
                db_session.add(self.test_district)

            self.test_mgmt = db_session.query(Management).filter_by(name='Тест Управление').first()
            if not self.test_mgmt:
                self.test_mgmt = Management(name='Тест Управление', code='ТУ', is_active=True)
                db_session.add(self.test_mgmt)

            self.test_plot = db_session.query(Plot).filter_by(name='Тест Участок').first()
            if not self.test_plot:
                self.test_plot = Plot(name='Тест Участок', code='ТУЧ', is_active=True)
                db_session.add(self.test_plot)

            self.test_type = db_session.query(AppealType).filter_by(name='Тест Тип').first()
            if not self.test_type:
                self.test_type = AppealType(name='Тест Тип', code='ТТ', is_active=True)
                db_session.add(self.test_type)

            self.test_topic = db_session.query(Topic).filter_by(name='Тест Тематика').first()
            if not self.test_topic:
                self.test_topic = Topic(name='Тест Тематика', code='ТТЕМ', is_active=True)
                db_session.add(self.test_topic)

            self.test_result = db_session.query(Result).filter_by(name='Тест Результат').first()
            if not self.test_result:
                self.test_result = Result(name='Тест Результат', code='ТРЕЗ', is_active=True)
                db_session.add(self.test_result)

            db_session.commit()

            # Cache IDs
            self.source_id = self.test_source.id
            self.district_id = self.test_district.id
            self.mgmt_id = self.test_mgmt.id
            self.plot_id = self.test_plot.id
            self.type_id = self.test_type.id
            self.topic_id = self.test_topic.id
            self.result_id = self.test_result.id

    def tearDown(self):
        # Clean up any test records created during test execution
        try:
            db_session.query(Appeal).delete()
            db_session.execute(management_districts.delete())
            db_session.execute(management_plots.delete())
            db_session.query(Management).delete()
            db_session.query(District).delete()
            db_session.query(Plot).delete()
            db_session.query(Source).delete()
            db_session.query(AppealType).delete()
            db_session.query(Topic).delete()
            db_session.query(Result).delete()
            db_session.query(User).filter_by(is_builtin=False).delete()
            db_session.commit()
        except Exception:
            db_session.rollback()
        finally:
            db_session.remove()

    def login(self, username, password):
        return self.client.post('/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)

    def logout(self):
        return self.client.get('/logout', follow_redirects=True)

    def test_superadmin_protected(self):
        """Test that built-in superadmin exists and cannot be deleted, edited or disabled."""
        with self.app.app_context():
            admin = db_session.query(User).filter_by(username=Config.SUPERADMIN_USERNAME).first()
            self.assertIsNotNone(admin)
            self.assertTrue(admin.is_builtin)
            self.assertTrue(admin.is_active)
            self.assertEqual(admin.role, 'superadmin')
            admin_id = admin.id

        # Log in as superadmin
        self.login(Config.SUPERADMIN_USERNAME, Config.SUPERADMIN_PASSWORD)

        # Attempt to delete built-in superadmin
        resp = self.client.post(f'/admin/users/{admin_id}/delete', follow_redirects=True)
        self.assertIn('Встроенную учетную запись superadmin нельзя удалить'.encode('utf-8'), resp.data)

        # Attempt to disable built-in superadmin
        resp = self.client.post(f'/admin/users/{admin_id}/toggle-status', follow_redirects=True)
        self.assertIn('Встроенную учетную запись superadmin нельзя отключить'.encode('utf-8'), resp.data)

        # Attempt to edit built-in superadmin
        resp = self.client.post(f'/admin/users/{admin_id}/edit', data={
            'full_name': 'Changed Name',
            'role': 'registrator'
        }, follow_redirects=True)
        self.assertIn('Встроенную учетную запись superadmin нельзя изменить'.encode('utf-8'), resp.data)

        # Verify DB record didn't change
        with self.app.app_context():
            admin_after = db_session.get(User, admin_id)
            self.assertTrue(admin_after.is_builtin)
            self.assertTrue(admin_after.is_active)
            self.assertEqual(admin_after.role, 'superadmin')

    def test_registrator_create_appeal_and_validation(self):
        """Test appeal creation by registrator, reg_date <= today validation, and required fields."""
        self.login('test_registrator', 'TestPass2026!')

        today = date.today()
        future_date = today + timedelta(days=2)

        # 1. Validation test: Future reg_date must fail
        resp = self.client.post('/appeals/new', data={
            'reg_date': future_date.strftime('%Y-%m-%d'),
            'number': 'TEST-FUTURE-001',
            'source_id': self.source_id,
            'district_id': self.district_id,
            'appeal_type_id': self.type_id,
            'topic_id': self.topic_id,
        }, follow_redirects=True)
        self.assertIn('не может быть больше текущей даты'.encode('utf-8'), resp.data)

        # 2. Validation test: Missing required number must fail
        resp = self.client.post('/appeals/new', data={
            'reg_date': today.strftime('%Y-%m-%d'),
            'number': '',
            'source_id': self.source_id,
            'district_id': self.district_id,
            'appeal_type_id': self.type_id,
            'topic_id': self.topic_id,
        }, follow_redirects=True)
        self.assertIn('№ обращения обязателен'.encode('utf-8'), resp.data)

        # 3. Successful creation: European format, status 'В работе', optional fields
        deadline = today + timedelta(days=10)
        resp = self.client.post('/appeals/new', data={
            'reg_date': today.strftime('%Y-%m-%d'),
            'number': 'TEST-VALID-2026',
            'source_id': self.source_id,
            'district_id': self.district_id,
            'appeal_type_id': self.type_id,
            'topic_id': self.topic_id,
            'applicant_gender': 'мужской',
            'validity': 'обоснован',
            'recurrence': 'Первичное',
            'deadline_date': deadline.strftime('%Y-%m-%d'),
            'comment': 'Тестовый комментарий для проверки сохранения',
        }, follow_redirects=True)
        self.assertIn('успешно зарегистрировано со статусом'.encode('utf-8'), resp.data)
        self.assertIn('В работе'.encode('utf-8'), resp.data)

        # Check DB
        with self.app.app_context():
            created = db_session.query(Appeal).filter_by(number='TEST-VALID-2026').first()
            self.assertIsNotNone(created)
            self.assertEqual(created.status, 'В работе')
            self.assertEqual(created.reg_date, today)
            self.assertEqual(created.deadline_date, deadline)
            self.assertEqual(created.days_until_deadline, 10)
            self.assertTrue(created.is_serviced)
            self.assertIsNotNone(created.created_at)
            self.assertIsNotNone(created.created_by_id)

    def test_close_appeal_and_lock_editing(self):
        """Test closing appeal: editing becomes impossible, closed_at and closed_by set."""
        self.login('test_registrator', 'TestPass2026!')

        today = date.today()
        with self.app.app_context():
            user = db_session.query(User).filter_by(username='test_registrator').first()

            appeal = Appeal(
                number='TEST-TO-CLOSE-01',
                reg_date=today,
                status='В работе',
                source_id=self.source_id,
                district_id=self.district_id,
                appeal_type_id=self.type_id,
                topic_id=self.topic_id,
                created_by_id=user.id,
                created_at=datetime.now()
            )
            db_session.add(appeal)
            db_session.commit()
            appeal_id = appeal.id

        # Close the appeal
        resp = self.client.post(f'/appeals/{appeal_id}/close', follow_redirects=True)
        self.assertIn('успешно закрыто'.encode('utf-8'), resp.data)
        self.assertIn('Редактирование карточки заблокировано'.encode('utf-8'), resp.data)

        # Check DB state
        with self.app.app_context():
            appeal_closed = db_session.get(Appeal, appeal_id)
            self.assertEqual(appeal_closed.status, 'Закрыто')
            self.assertIsNotNone(appeal_closed.closed_at)
            self.assertIsNotNone(appeal_closed.closed_by_id)
            self.assertTrue(appeal_closed.is_closed)

        # Attempt to edit closed appeal -> MUST BE REJECTED!
        resp_edit = self.client.post(f'/appeals/{appeal_id}/edit', data={
            'reg_date': today.strftime('%Y-%m-%d'),
            'number': 'ATTEMPT-TO-EDIT',
            'source_id': self.source_id,
            'district_id': self.district_id,
            'appeal_type_id': self.type_id,
            'topic_id': self.topic_id,
        }, follow_redirects=True)
        self.assertIn('Редактирование закрытого обращения невозможно'.encode('utf-8'), resp_edit.data)

        # Verify DB number was NOT changed
        with self.app.app_context():
            appeal_check = db_session.get(Appeal, appeal_id)
            self.assertEqual(appeal_check.number, 'TEST-TO-CLOSE-01')

    def test_main_page_filters_and_columns(self):
        """Test main page columns, tabs, and filters."""
        self.login('test_registrator', 'TestPass2026!')

        # Create an appeal
        with self.app.app_context():
            user = db_session.query(User).filter_by(username='test_registrator').first()
            appeal = Appeal(
                number='TEST-FILTER-99',
                reg_date=date.today(),
                status='В работе',
                source_id=self.source_id,
                district_id=self.district_id,
                appeal_type_id=self.type_id,
                topic_id=self.topic_id,
                created_by_id=user.id,
                created_at=datetime.now()
            )
            db_session.add(appeal)
            db_session.commit()

        # 1. Main page active tab
        resp = self.client.get('/?tab=active')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('В работе'.encode('utf-8'), resp.data)
        self.assertIn('Номер обращения'.encode('utf-8'), resp.data)
        self.assertIn('Округ'.encode('utf-8'), resp.data)
        self.assertIn('Управление'.encode('utf-8'), resp.data)
        self.assertIn('Тип обращения'.encode('utf-8'), resp.data)
        self.assertIn('Состоит на обслуживании'.encode('utf-8'), resp.data)
        self.assertIn('Срок ответа в количестве дней'.encode('utf-8'), resp.data)

        # 2. Main page closed tab
        resp_closed = self.client.get('/?tab=closed')
        self.assertEqual(resp_closed.status_code, 200)
        self.assertIn('Закрытые обращения'.encode('utf-8'), resp_closed.data)

        # 3. Filter by number
        resp_filt = self.client.get('/?tab=active&number=FILTER-99')
        self.assertEqual(resp_filt.status_code, 200)
        self.assertIn('TEST-FILTER-99'.encode('utf-8'), resp_filt.data)

    def test_admin_reference_relations(self):
        """Test dictionary management and management relations (districts, plots)."""
        self.login(Config.SUPERADMIN_USERNAME, Config.SUPERADMIN_PASSWORD)

        # Update relations via POST
        resp = self.client.post('/admin/relations', data={
            'management_id': self.mgmt_id,
            'district_ids': [self.district_id],
            'plot_ids': [self.plot_id],
        }, follow_redirects=True)
        self.assertIn('Связи для управления'.encode('utf-8'), resp.data)

        # Verify DB
        with self.app.app_context():
            m = db_session.get(Management, self.mgmt_id)
            self.assertIn(self.district_id, [d.id for d in m.districts])
            self.assertIn(self.plot_id, [p.id for p in m.plots])

    def test_create_appeal_minimal_fields(self):
        """Test appeal creation with only mandatory fields."""
        self.login('test_registrator', 'TestPass2026!')
        today = date.today()

        resp = self.client.post('/appeals/new', data={
            'reg_date': today.strftime('%Y-%m-%d'),
            'number': 'TEST-MINIMAL-01',
            'source_id': self.source_id,
            'district_id': self.district_id,
            'appeal_type_id': self.type_id,
            'topic_id': self.topic_id,
            # All optional fields omitted:
            'management_id': '',
            'plot_id': '',
            'applicant_gender': '',
            'validity': '',
            'recurrence': '',
            'result_id': '',
            'deadline_date': '',
            'comment': '',
        }, follow_redirects=True)

        self.assertIn('успешно зарегистрировано со статусом'.encode('utf-8'), resp.data)

        with self.app.app_context():
            created = db_session.query(Appeal).filter_by(number='TEST-MINIMAL-01').first()
            self.assertIsNotNone(created)
            self.assertIsNone(created.management_id)
            self.assertIsNone(created.plot_id)
            self.assertIsNone(created.applicant_gender)
            self.assertIsNone(created.validity)
            self.assertIsNone(created.recurrence)
            self.assertIsNone(created.result_id)
            self.assertIsNone(created.deadline_date)
            self.assertFalse(created.not_serviced)
            self.assertTrue(created.is_serviced)

    def test_find_available_port_fallback(self):
        """Test finding available port when initial port is occupied."""
        import socket

        # Create a dummy socket listening on an arbitrary free port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(('0.0.0.0', 0))
            sock.listen(1)
            busy_port = sock.getsockname()[1]

            # The busy_port must be unavailable
            self.assertFalse(is_port_available(busy_port, '0.0.0.0'))

            # find_available_port starting from busy_port must return > busy_port
            next_port = find_available_port(start_port=busy_port, host='0.0.0.0')
            self.assertGreater(next_port, busy_port)
            self.assertTrue(is_port_available(next_port, '0.0.0.0'))


if __name__ == '__main__':
    unittest.main()
