import unittest
from datetime import date, datetime, timedelta
from app import create_app
from app.config import Config
from app.database import db_session, init_db
from app.models import (
    User, Appeal, Source, District, Management, Plot, AppealType, Topic, Result
)
from app.utils import parse_date, format_date_eur


class AppealsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        with self.app.app_context():
            init_db()

    def tearDown(self):
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
        self.login('registrator1', 'RegistratorPass2026!')

        today = date.today()
        future_date = today + timedelta(days=2)

        with self.app.app_context():
            source = db_session.query(Source).first()
            district = db_session.query(District).first()
            appeal_type = db_session.query(AppealType).first()
            topic = db_session.query(Topic).first()

        # 1. Validation test: Future reg_date must fail
        resp = self.client.post('/appeals/new', data={
            'reg_date': future_date.strftime('%Y-%m-%d'),
            'number': 'TEST-FUTURE-001',
            'source_id': source.id,
            'district_id': district.id,
            'appeal_type_id': appeal_type.id,
            'topic_id': topic.id,
        }, follow_redirects=True)
        self.assertIn('не может быть больше текущей даты'.encode('utf-8'), resp.data)

        # 2. Validation test: Missing required number must fail
        resp = self.client.post('/appeals/new', data={
            'reg_date': today.strftime('%Y-%m-%d'),
            'number': '',
            'source_id': source.id,
            'district_id': district.id,
            'appeal_type_id': appeal_type.id,
            'topic_id': topic.id,
        }, follow_redirects=True)
        self.assertIn('№ обращения обязателен'.encode('utf-8'), resp.data)

        # 3. Successful creation: European format, status 'В работе', optional fields
        deadline = today + timedelta(days=10)
        resp = self.client.post('/appeals/new', data={
            'reg_date': today.strftime('%Y-%m-%d'),
            'number': 'TEST-VALID-2026',
            'source_id': source.id,
            'district_id': district.id,
            'appeal_type_id': appeal_type.id,
            'topic_id': topic.id,
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
        self.login('registrator1', 'RegistratorPass2026!')

        today = date.today()
        with self.app.app_context():
            source = db_session.query(Source).first()
            district = db_session.query(District).first()
            appeal_type = db_session.query(AppealType).first()
            topic = db_session.query(Topic).first()
            user = db_session.query(User).filter_by(username='registrator1').first()

            source_id = source.id
            district_id = district.id
            appeal_type_id = appeal_type.id
            topic_id = topic.id

            appeal = Appeal(
                number='TEST-TO-CLOSE-01',
                reg_date=today,
                status='В работе',
                source_id=source_id,
                district_id=district_id,
                appeal_type_id=appeal_type_id,
                topic_id=topic_id,
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
            'source_id': source_id,
            'district_id': district_id,
            'appeal_type_id': appeal_type_id,
            'topic_id': topic_id,
        }, follow_redirects=True)
        self.assertIn('Редактирование закрытого обращения невозможно'.encode('utf-8'), resp_edit.data)

        # Verify DB number was NOT changed
        with self.app.app_context():
            appeal_check = db_session.get(Appeal, appeal_id)
            self.assertEqual(appeal_check.number, 'TEST-TO-CLOSE-01')

    def test_main_page_filters_and_columns(self):
        """Test main page columns, tabs, and filters."""
        self.login('registrator1', 'RegistratorPass2026!')

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
        resp_filt = self.client.get('/?tab=active&number=00101')
        self.assertEqual(resp_filt.status_code, 200)
        self.assertIn('ОГ-2026-00101'.encode('utf-8'), resp_filt.data)

    def test_admin_reference_relations(self):
        """Test dictionary management and management relations (districts, plots)."""
        self.login(Config.SUPERADMIN_USERNAME, Config.SUPERADMIN_PASSWORD)

        with self.app.app_context():
            mgmt = db_session.query(Management).first()
            district = db_session.query(District).first()
            plot = db_session.query(Plot).first()
            mgmt_id = mgmt.id
            dist_id = district.id
            plot_id = plot.id

        # Update relations via POST
        resp = self.client.post('/admin/relations', data={
            'management_id': mgmt_id,
            'district_ids': [dist_id],
            'plot_ids': [plot_id],
        }, follow_redirects=True)
        self.assertIn('Связи для управления'.encode('utf-8'), resp.data)

        # Verify DB
        with self.app.app_context():
            m = db_session.get(Management, mgmt_id)
            self.assertIn(dist_id, [d.id for d in m.districts])
            self.assertIn(plot_id, [p.id for p in m.plots])


    def test_create_appeal_minimal_fields(self):
        """Test appeal creation with only mandatory fields."""
        self.login('registrator1', 'RegistratorPass2026!')
        today = date.today()

        with self.app.app_context():
            source = db_session.query(Source).first()
            district = db_session.query(District).first()
            appeal_type = db_session.query(AppealType).first()
            topic = db_session.query(Topic).first()

            resp = self.client.post('/appeals/new', data={
                'reg_date': today.strftime('%Y-%m-%d'),
                'number': 'TEST-MINIMAL-01',
                'source_id': source.id,
                'district_id': district.id,
                'appeal_type_id': appeal_type.id,
                'topic_id': topic.id,
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
        from run import is_port_available, find_available_port

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
