from datetime import date, datetime, timedelta
from app import create_app
from app.database import db_session, init_db
from app.models import (
    User, Source, District, Management, Plot, AppealType, Topic, Result, Appeal
)

app = create_app()


def seed_data():
    with app.app_context():
        init_db()

        # 1. Create a default registrator user if not exists
        registrator = db_session.query(User).filter_by(username='registrator1').first()
        if not registrator:
            registrator = User(
                username='registrator1',
                full_name='Иванова Мария Сергеевна',
                role='registrator',
                is_builtin=False,
                is_active=True
            )
            registrator.set_password('RegistratorPass2026!')
            db_session.add(registrator)
            db_session.commit()
            print('Created user: registrator1 / RegistratorPass2026!')

        superadmin = db_session.query(User).filter_by(username=app.config['SUPERADMIN_USERNAME']).first()

        # 2. Seed Sources (Источники поступления)
        sources_data = [
            ('Портал Госуслуг', 'ЕПГУ'),
            ('Электронная приемная Правительства', 'ЭП'),
            ('Почта России (письменное)', 'ПР'),
            ('Личный прием граждан', 'ЛП'),
            ('Горячая телефонная линия', 'ГЛ'),
            ('Многофункциональный центр (МФЦ)', 'МФЦ'),
        ]
        for name, code in sources_data:
            if not db_session.query(Source).filter_by(name=name).first():
                db_session.add(Source(name=name, code=code, is_active=True))
        db_session.commit()

        # 3. Seed Districts (Округа)
        districts_data = [
            ('Центральный административный округ', 'ЦАО'),
            ('Северный административный округ', 'САО'),
            ('Северо-Восточный административный округ', 'СВАО'),
            ('Восточный административный округ', 'ВАО'),
            ('Юго-Восточный административный округ', 'ЮВАО'),
            ('Южный административный округ', 'ЮАО'),
            ('Юго-Западный административный округ', 'ЮЗАО'),
            ('Западный административный округ', 'ЗАО'),
            ('Северо-Западный административный округ', 'СЗАО'),
        ]
        for name, code in districts_data:
            if not db_session.query(District).filter_by(name=name).first():
                db_session.add(District(name=name, code=code, is_active=True))
        db_session.commit()

        # 4. Seed Managements (Управления)
        managements_data = [
            ('Управление жилищно-коммунального хозяйства и благоустройства', 'УЖКХиБ'),
            ('Управление дорожно-транспортной инфраструктуры', 'УДТИ'),
            ('Управление социальной защиты населения', 'УСЗН'),
            ('Управление градостроительного регулирования', 'УГР'),
            ('Управление потребительского рынка и услуг', 'УПРиУ'),
        ]
        for name, code in managements_data:
            if not db_session.query(Management).filter_by(name=name).first():
                db_session.add(Management(name=name, code=code, is_active=True))
        db_session.commit()

        # 5. Seed Plots (Участки)
        plots_data = [
            ('Участок жилищной эксплуатации № 1', 'УЭ-1'),
            ('Участок жилищной эксплуатации № 2', 'УЭ-2'),
            ('Аварийно-диспетчерский участок № 3', 'АДУ-3'),
            ('Участок благоустройства и озеленения № 4', 'УБО-4'),
            ('Дорожно-ремонтный участок № 5', 'ДРУ-5'),
        ]
        for name, code in plots_data:
            if not db_session.query(Plot).filter_by(name=name).first():
                db_session.add(Plot(name=name, code=code, is_active=True))
        db_session.commit()

        # 6. Seed Appeal Types (Типы обращений)
        types_data = [
            ('Заявление', 'ЗАЯВ'),
            ('Жалоба', 'ЖАЛ'),
            ('Предложение', 'ПРЕДЛ'),
            ('Запрос информации', 'ЗАПР'),
            ('Претензия', 'ПРЕТ'),
        ]
        for name, code in types_data:
            if not db_session.query(AppealType).filter_by(name=name).first():
                db_session.add(AppealType(name=name, code=code, is_active=True))
        db_session.commit()

        # 7. Seed Topics (Тематики обращений)
        topics_data = [
            ('Содержание и ремонт общего имущества в МКД', 'Т-01'),
            ('Уборка дворовых территорий и вывоз мусора', 'Т-02'),
            ('Ремонт асфальтового покрытия и тротуаров', 'Т-03'),
            ('Организация дорожного движения и парковок', 'Т-04'),
            ('Качество коммунальных услуг (отопление, водоснабжение)', 'Т-05'),
            ('Благоустройство парков и детских площадок', 'Т-06'),
            ('Нарушение тишины и правил добрососедства', 'Т-07'),
            ('Социальная поддержка малоимущих категорий граждан', 'Т-08'),
        ]
        for name, code in topics_data:
            if not db_session.query(Topic).filter_by(name=name).first():
                db_session.add(Topic(name=name, code=code, is_active=True))
        db_session.commit()

        # 8. Seed Results (Результаты рассмотрения)
        results_data = [
            ('Разъяснено', 'РАЗ'),
            ('Удовлетворено', 'УДОВ'),
            ('Приняты оперативные меры', 'МЕРЫ'),
            ('Отказано в удовлетворении', 'ОТК'),
            ('Перенаправлено по подведомственности', 'ПЕРЕНАПР'),
            ('Оставлено без рассмотрения', 'БЕЗ_РАССМ'),
        ]
        for name, code in results_data:
            if not db_session.query(Result).filter_by(name=name).first():
                db_session.add(Result(name=name, code=code, is_active=True))
        db_session.commit()

        # 9. Establish Dependencies: Management -> Districts and Plots
        # "зависимости между справочниками в Управление может входить несколько округов, в управление может входить несколько участков"
        ujkh = db_session.query(Management).filter_by(code='УЖКХиБ').first()
        udti = db_session.query(Management).filter_by(code='УДТИ').first()
        uszn = db_session.query(Management).filter_by(code='УСЗН').first()

        cao = db_session.query(District).filter_by(code='ЦАО').first()
        sao = db_session.query(District).filter_by(code='САО').first()
        svao = db_session.query(District).filter_by(code='СВАО').first()
        vao = db_session.query(District).filter_by(code='ВАО').first()
        yuao = db_session.query(District).filter_by(code='ЮАО').first()

        p1 = db_session.query(Plot).filter_by(code='УЭ-1').first()
        p2 = db_session.query(Plot).filter_by(code='УЭ-2').first()
        p3 = db_session.query(Plot).filter_by(code='АДУ-3').first()
        p4 = db_session.query(Plot).filter_by(code='УБО-4').first()
        p5 = db_session.query(Plot).filter_by(code='ДРУ-5').first()

        if ujkh and not ujkh.districts:
            ujkh.districts = [cao, sao, svao]
            ujkh.plots = [p1, p2, p4]

        if udti and not udti.districts:
            udti.districts = [vao, yuao, cao]
            udti.plots = [p3, p5]

        if uszn and not uszn.districts:
            uszn.districts = [cao, sao]
            uszn.plots = [p1]

        db_session.commit()

        # 10. Seed Sample Appeals if none exist
        if db_session.query(Appeal).count() == 0:
            today = date.today()

            # Active appeal 1: due in 5 days
            appeal1 = Appeal(
                number='ОГ-2026-00101',
                reg_date=today - timedelta(days=2),
                status='В работе',
                source_id=db_session.query(Source).filter_by(code='ЕПГУ').first().id,
                district_id=cao.id,
                management_id=ujkh.id,
                plot_id=p1.id,
                applicant_gender='мужской',
                appeal_type_id=db_session.query(AppealType).filter_by(code='ЖАЛ').first().id,
                topic_id=db_session.query(Topic).filter_by(code='Т-01').first().id,
                validity='обоснован',
                recurrence='Первичное',
                deadline_date=today + timedelta(days=5),
                not_serviced=False,  # Состоит на обслуживании: Да
                comment='Жалоба на протечку стояка отопления на 4-м этаже.',
                created_by_id=registrator.id,
                created_at=datetime.now() - timedelta(days=2),
            )

            # Active appeal 2: due today (urgent)
            appeal2 = Appeal(
                number='ОГ-2026-00102',
                reg_date=today - timedelta(days=10),
                status='В работе',
                source_id=db_session.query(Source).filter_by(code='ЭП').first().id,
                district_id=sao.id,
                management_id=ujkh.id,
                plot_id=p4.id,
                applicant_gender='женский',
                appeal_type_id=db_session.query(AppealType).filter_by(code='ЗАЯВ').first().id,
                topic_id=db_session.query(Topic).filter_by(code='Т-02').first().id,
                validity=None,
                recurrence='Повторное',
                deadline_date=today,
                not_serviced=True,  # Состоит на обслуживании: Нет
                comment='Просьба ликвидировать несанкционированную свалку строительных отходов.',
                created_by_id=registrator.id,
                created_at=datetime.now() - timedelta(days=10),
            )

            # Active appeal 3: overdue by 3 days
            appeal3 = Appeal(
                number='ОГ-2026-00103',
                reg_date=today - timedelta(days=15),
                status='В работе',
                source_id=db_session.query(Source).filter_by(code='ПР').first().id,
                district_id=vao.id,
                management_id=udti.id,
                plot_id=p5.id,
                applicant_gender='мужской',
                appeal_type_id=db_session.query(AppealType).filter_by(code='ПРЕТ').first().id,
                topic_id=db_session.query(Topic).filter_by(code='Т-03').first().id,
                validity='обоснован',
                recurrence='Первичное',
                deadline_date=today - timedelta(days=3),
                not_serviced=False,  # Состоит на обслуживании: Да
                comment='Выбоина глубиной более 12 см на проезжей части напротив дома 14.',
                created_by_id=registrator.id,
                created_at=datetime.now() - timedelta(days=15),
            )

            # Active appeal 4: without deadline
            appeal4 = Appeal(
                number='ОГ-2026-00104',
                reg_date=today,
                status='В работе',
                source_id=db_session.query(Source).filter_by(code='ЛП').first().id,
                district_id=svao.id,
                management_id=None,
                plot_id=None,
                applicant_gender='женский',
                appeal_type_id=db_session.query(AppealType).filter_by(code='ПРЕДЛ').first().id,
                topic_id=db_session.query(Topic).filter_by(code='Т-06').first().id,
                validity=None,
                recurrence='Первичное',
                deadline_date=None,
                not_serviced=False,  # Состоит на обслуживании: Да
                comment='Предложение по обустройству велодорожки в районном сквере.',
                created_by_id=superadmin.id,
                created_at=datetime.now(),
            )

            # Closed appeal 1
            appeal5 = Appeal(
                number='ОГ-2026-00088',
                reg_date=today - timedelta(days=20),
                status='Закрыто',
                source_id=db_session.query(Source).filter_by(code='МФЦ').first().id,
                district_id=cao.id,
                management_id=ujkh.id,
                plot_id=p2.id,
                applicant_gender='женский',
                appeal_type_id=db_session.query(AppealType).filter_by(code='ЖАЛ').first().id,
                topic_id=db_session.query(Topic).filter_by(code='Т-05').first().id,
                validity='обоснован',
                recurrence='Первичное',
                result_id=db_session.query(Result).filter_by(code='МЕРЫ').first().id,
                deadline_date=today - timedelta(days=5),
                not_serviced=False,
                comment='Вопрос решен, произведена наладка регулятора давления горячего водоснабжения.',
                created_by_id=registrator.id,
                created_at=datetime.now() - timedelta(days=20),
                closed_by_id=superadmin.id,
                closed_at=datetime.now() - timedelta(days=6),
            )

            # Closed appeal 2
            appeal6 = Appeal(
                number='ОГ-2026-00072',
                reg_date=today - timedelta(days=35),
                status='Закрыто',
                source_id=db_session.query(Source).filter_by(code='ГЛ').first().id,
                district_id=yuao.id,
                management_id=udti.id,
                plot_id=p3.id,
                applicant_gender='мужской',
                appeal_type_id=db_session.query(AppealType).filter_by(code='ЗАПР').first().id,
                topic_id=db_session.query(Topic).filter_by(code='Т-04').first().id,
                validity='не обоснован',
                recurrence='Многократное',
                result_id=db_session.query(Result).filter_by(code='РАЗ').first().id,
                deadline_date=today - timedelta(days=15),
                not_serviced=True,
                comment='Гражданину направлены подробные разъяснения схемы организации парковочного пространства.',
                created_by_id=registrator.id,
                created_at=datetime.now() - timedelta(days=35),
                closed_by_id=registrator.id,
                closed_at=datetime.now() - timedelta(days=16),
            )

            db_session.add_all([appeal1, appeal2, appeal3, appeal4, appeal5, appeal6])
            db_session.commit()
            print('Sample appeals created successfully!')

        print('Database seed completed successfully!')


if __name__ == '__main__':
    seed_data()
