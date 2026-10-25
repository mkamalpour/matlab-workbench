"""Validated, deterministic coursework transport simulator. No real transactions."""
import copy
import re

CATEGORIES = {'BIKE', 'VAN', 'TRUCK'}
POSITION = r'\(\s*([+-]?\d+)\s*,\s*([+-]?\d+)\s*\)'
USERNAME = r'[A-Za-z0-9_-]{1,64}'


def _coordinate(value):
    if not isinstance(value, (list, tuple)) or len(value) != 2 or any(type(number) is not int for number in value):
        raise ValueError('Coordinates must be pairs of integers.')
    if any(abs(number) > 10 ** 9 for number in value):
        raise ValueError('Coordinates must lie between -1000000000 and 1000000000.')
    return list(value)


class TransportSystem:
    def __init__(self):
        self.drivers = {}
        self.active = []
        self.completed = []
        self.next_order_id = 1

    def execute(self, command):
        command = command.strip()
        if command.lower() == 'exit':
            return dict(action='exit', message='Command session finished. Simulator state is preserved.')
        match = re.fullmatch(rf'ADD-DRIVER\s+({USERNAME})\s+{POSITION}\s+(\w+)', command, re.I)
        if match:
            username, x, y, category = match.groups()
            category = category.upper()
            if category not in CATEGORIES:
                raise ValueError('Category must be BIKE, VAN or TRUCK.')
            if username in self.drivers:
                raise ValueError('This driver username is already registered.')
            coordinates = _coordinate([int(x), int(y)])
            self.drivers[username] = dict(username=username, x=coordinates[0], y=coordinates[1], category=category)
            return dict(action='add_driver', message=f'Driver {username} registered.')
        match = re.fullmatch(rf'CREATE-ORDER\s+(\w+)\s+{POSITION}\s+{POSITION}', command, re.I)
        if match:
            category, sx, sy, fx, fy = match.groups()
            category = category.upper()
            if category not in CATEGORIES:
                raise ValueError('Category must be BIKE, VAN or TRUCK.')
            start, finish = _coordinate([int(sx), int(sy)]), _coordinate([int(fx), int(fy)])
            busy = {order['username'] for order in self.active}
            available = [driver for driver in self.drivers.values() if driver['category'] == category and driver['username'] not in busy]
            if not available:
                raise ValueError(f'No available {category} driver. Register one or complete an active order.')
            driver = min(available, key=lambda item: (abs(item['x'] - start[0]) + abs(item['y'] - start[1]), item['username']))
            order = dict(order_id=self.next_order_id, username=driver['username'], category=category, start=start, finish=finish)
            self.active.append(order)
            self.next_order_id += 1
            return dict(action='create_order', message=f"Order {order['order_id']} assigned to {driver['username']}.", order=copy.deepcopy(order))
        match = re.fullmatch(rf'(?:RECEIVE|RECIEVE)-ORDER\s+{POSITION}\s+{POSITION}\s+({USERNAME})', command, re.I)
        if match:
            sx, sy, fx, fy, username = match.groups()
            start, finish = _coordinate([int(sx), int(sy)]), _coordinate([int(fx), int(fy)])
            order = next((order for order in self.active if order['username'] == username and order['start'] == start and order['finish'] == finish), None)
            if order is None:
                raise ValueError('No active order matches this driver, start and destination.')
            self.completed.append(order)
            self.active.remove(order)
            self.drivers[username].update(x=finish[0], y=finish[1])
            return dict(action='complete_order', message=f"Order {order['order_id']} completed; driver location updated.", order=copy.deepcopy(order))
        raise ValueError('Unknown command or invalid arguments. Use ADD-DRIVER, CREATE-ORDER, RECEIVE-ORDER or Exit.')

    def snapshot(self):
        return copy.deepcopy(dict(version=1, drivers=list(self.drivers.values()), active=self.active,
                                  completed=self.completed, next_order_id=self.next_order_id))

    @classmethod
    def from_snapshot(cls, data):
        if not isinstance(data, dict) or set(data) != {'version', 'drivers', 'active', 'completed', 'next_order_id'} or type(data['version']) is not int or data['version'] != 1:
            raise ValueError('Expected a version 1 transport snapshot with all required fields.')
        if any(not isinstance(data[field], list) for field in ('drivers', 'active', 'completed')):
            raise ValueError('Snapshot drivers and orders must be lists.')
        if type(data['next_order_id']) is not int or data['next_order_id'] < 1:
            raise ValueError('next_order_id must be a positive integer.')
        system = cls()
        for driver in data['drivers']:
            if not isinstance(driver, dict) or set(driver) != {'username', 'x', 'y', 'category'}:
                raise ValueError('Invalid snapshot driver fields.')
            username = driver['username']
            if not isinstance(username, str) or not re.fullmatch(USERNAME, username) or username in system.drivers:
                raise ValueError('Driver usernames must be valid and unique.')
            if not isinstance(driver['category'], str) or driver['category'] not in CATEGORIES:
                raise ValueError('Invalid driver category.')
            _coordinate([driver['x'], driver['y']])
            system.drivers[username] = copy.deepcopy(driver)
        seen_orders, busy = set(), set()
        for field in ('active', 'completed'):
            for order in data[field]:
                if not isinstance(order, dict) or set(order) != {'order_id', 'username', 'category', 'start', 'finish'}:
                    raise ValueError('Invalid snapshot order fields.')
                identifier, username = order['order_id'], order['username']
                if type(identifier) is not int or identifier < 1 or identifier in seen_orders or identifier >= data['next_order_id']:
                    raise ValueError('Order IDs must be unique positive integers below next_order_id.')
                if not isinstance(username, str) or username not in system.drivers or order['category'] != system.drivers[username]['category']:
                    raise ValueError('Every order must reference a registered driver with matching category.')
                normalized = copy.deepcopy(order)
                normalized['start'] = _coordinate(order['start'])
                normalized['finish'] = _coordinate(order['finish'])
                if field == 'active':
                    if username in busy:
                        raise ValueError('A driver cannot have two active orders.')
                    busy.add(username)
                seen_orders.add(identifier)
                getattr(system, field).append(normalized)
        system.next_order_id = data['next_order_id']
        return system

    def export_text_files(self):
        def position(values):
            return f'({values[0]},{values[1]})'
        def orders(items):
            return ''.join(f"{order['category']} {position(order['start'])} {position(order['finish'])} {order['username']}\n" for order in items)
        drivers = ''.join(f"{d['username']} ({d['x']},{d['y']}) {d['category']}\n" for d in self.drivers.values())
        return {'driver.txt': drivers, 'new_order.txt': orders(self.active), 'order.txt': orders(self.completed)}
