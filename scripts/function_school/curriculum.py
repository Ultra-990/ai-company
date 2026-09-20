"""Teacher-authored train contracts and independent tests, fixed before inference.

No reference implementation is supplied. All variants of these families belong
to train; these exercises cannot later be presented as a held-out benchmark.
"""

CASES = [
    {
        'id': 'inventory-checkout', 'family': 'function-school.inventory-checkout',
        'brief': '''Implement checkout(catalog, cart) in solution.py. Pure Python.
catalog is a dict mapping nonempty string SKUs to dicts with exactly price_cents
and stock, both nonnegative ints (bool is forbidden). Validate EVERY catalog
entry, including unused entries. cart is a list of dicts with exactly sku and
quantity: sku must be a catalog key, quantity a positive int, never bool.
Merge duplicate SKUs, preserving their first appearance in cart. Reject aggregate
quantity above stock. Return exactly {"items": [...], "total_cents": int,
"remaining": {...}}. Each item has exactly sku, quantity, unit_cents, line_cents.
remaining maps EVERY catalog SKU to remaining integer stock, including unused.
No float arithmetic. Empty cart is valid. Invalid inputs raise ValueError;
no input changes on success or failure, no returned mutable alias of inputs.''',
        'lessons': {
            'test_aggregate_stock': 'Aggregate all lines for a SKU before checking inventory; duplicate lines must not bypass the stock limit.',
            'test_money_and_order': 'Use integer cents and preserve first-seen product order when merging duplicate cart lines.',
            'test_invalid_unused_catalog': 'Validate the full input contract, including catalog entries not used by the current cart.',
            'test_no_mutation': 'Build independent result structures; neither a successful operation nor a rejected operation may mutate caller state.',
        },
        'tests': '''import copy
import unittest
from solution import checkout

class Checks(unittest.TestCase):
    def catalog(self):
        return {'pl': {'price_cents': 199, 'stock': 4}, 'no': {'price_cents': 301, 'stock': 3}, 'free': {'price_cents': 0, 'stock': 1}}
    def test_money_and_order(self):
        result = checkout(self.catalog(), [{'sku':'no','quantity':1}, {'sku':'pl','quantity':2}, {'sku':'no','quantity':2}])
        self.assertEqual(result, {'items':[
            {'sku':'no','quantity':3,'unit_cents':301,'line_cents':903},
            {'sku':'pl','quantity':2,'unit_cents':199,'line_cents':398}],
            'total_cents':1301, 'remaining':{'pl':2,'no':0,'free':1}})
    def test_aggregate_stock(self):
        with self.assertRaises(ValueError):
            checkout(self.catalog(), [{'sku':'pl','quantity':3}, {'sku':'pl','quantity':2}])
    def test_zero_and_large_money(self):
        self.assertEqual(checkout(self.catalog(), [{'sku':'free','quantity':1}])['total_cents'], 0)
        big = 10**30 + 7
        result = checkout({'x':{'price_cents':big,'stock':9}}, [{'sku':'x','quantity':7}])
        self.assertEqual(result['total_cents'], big*7)
        self.assertIs(type(result['total_cents']), int)
    def test_empty(self):
        self.assertEqual(checkout({}, []), {'items':[],'total_cents':0,'remaining':{}})
        self.assertEqual(checkout(self.catalog(), [])['remaining'], {'pl':4,'no':3,'free':1})
    def test_invalid_unused_catalog(self):
        for entry in [{'price_cents':True,'stock':1}, {'price_cents':1,'stock':False},
                      {'price_cents':1.0,'stock':1}, {'price_cents':-1,'stock':1},
                      {'price_cents':0,'stock':-1}, {'stock':1},
                      {'price_cents':1,'stock':1,'extra':1}, None]:
            with self.subTest(entry=entry), self.assertRaises(ValueError):
                checkout(self.catalog() | {'unused':entry}, [])
        for value in [[], None, {'':{'price_cents':1,'stock':1}}, {1:{'price_cents':1,'stock':1}}]:
            with self.subTest(value=value), self.assertRaises(ValueError): checkout(value, [])
    def test_invalid_cart(self):
        for value in [None, {}, (), [{'sku':'absent','quantity':1}]]:
            with self.subTest(value=value), self.assertRaises(ValueError): checkout(self.catalog(), value)
        for q in [True, False, 0, -1, 1.0, '1', None]:
            with self.subTest(q=q), self.assertRaises(ValueError): checkout(self.catalog(), [{'sku':'pl','quantity':q}])
        for line in [None, [], {}, {'sku':[],'quantity':1}, {'sku':'pl','quantity':1,'extra':0}]:
            with self.subTest(line=line), self.assertRaises(ValueError): checkout(self.catalog(), [line])
    def test_no_mutation(self):
        catalog = self.catalog(); cart = [{'sku':'pl','quantity':2}]
        original = copy.deepcopy((catalog,cart)); result = checkout(catalog,cart)
        self.assertEqual((catalog,cart),original)
        result['items'][0]['quantity'] = 999; result['remaining']['pl'] = 999
        self.assertEqual((catalog,cart),original)
        bad = cart + [{'sku':'no','quantity':99}]; before = copy.deepcopy((catalog,bad))
        with self.assertRaises(ValueError): checkout(catalog,bad)
        self.assertEqual((catalog,bad),before)
    def test_conservation(self):
        for stock in range(1,18):
            for quantity in range(1,stock+1):
                result = checkout({'x':{'price_cents':137,'stock':stock}}, [{'sku':'x','quantity':quantity}])
                self.assertEqual(result['remaining']['x'] + result['items'][0]['quantity'], stock)
                self.assertEqual(result['total_cents'], quantity*137)
''',
    },
    {
        'id': 'event-waitlist', 'family': 'function-school.event-waitlist',
        'brief': '''Implement allocate(capacity, requests, cancelled) in solution.py.
capacity is a nonnegative int, not bool. requests is a list of dicts with exactly
id (nonempty str) and seats (positive int, not bool). Repeated id with identical
seats is an idempotent retry: count it once, at its first position. A repeated id
with different seats raises ValueError, even if cancelled. cancelled is a list
of nonempty string IDs; duplicates and unknown IDs are allowed and ignored.
Validate ALL inputs before allocation, including cancelled requests. Remove
cancelled requests before allocation, then serve remaining unique requests FIFO.
The first request that does not fit and ALL subsequent requests go to waitlist:
smaller requests never jump the queue. A request larger than capacity is valid
but blocks the queue. Return exactly {"confirmed": [ids], "waitlist": [ids],
"remaining": integer}. Empty inputs and zero capacity are valid. Invalid input
raises ValueError. Never mutate inputs or return mutable aliases.''',
        'lessons': {
            'test_no_queue_jumping': 'A strict FIFO waiting list stays blocked after the first request that cannot fit, even if later requests are smaller.',
            'test_cancellation_before_allocation': 'Validate first, then remove cancellations before allocating capacity; do not validate only active requests.',
            'test_idempotency_and_conflict': 'Identical request IDs are retries only when their payloads match; conflicts must fail even for cancelled IDs.',
        },
        'tests': '''import copy
import unittest
from solution import allocate

class Checks(unittest.TestCase):
    def test_no_queue_jumping(self):
        self.assertEqual(allocate(5,[{'id':'a','seats':3},{'id':'b','seats':4},{'id':'c','seats':1}],[]),
                         {'confirmed':['a'],'waitlist':['b','c'],'remaining':2})
        self.assertEqual(allocate(2,[{'id':'large','seats':3},{'id':'small','seats':1}],[]),
                         {'confirmed':[],'waitlist':['large','small'],'remaining':2})
    def test_cancellation_before_allocation(self):
        req=[{'id':'a','seats':3},{'id':'b','seats':4},{'id':'c','seats':1}]
        self.assertEqual(allocate(5,req,['a','missing','a']), {'confirmed':['b','c'],'waitlist':[],'remaining':0})
        with self.assertRaises(ValueError): allocate(5,[{'id':'a','seats':False}],['a'])
    def test_idempotency_and_conflict(self):
        req=[{'id':'a','seats':2},{'id':'a','seats':2},{'id':'b','seats':1}]
        self.assertEqual(allocate(3,req,[]), {'confirmed':['a','b'],'waitlist':[],'remaining':0})
        for cancelled in [[], ['a']]:
            with self.subTest(cancelled=cancelled), self.assertRaises(ValueError):
                allocate(9,[{'id':'a','seats':2},{'id':'a','seats':1}],cancelled)
    def test_empty_and_zero(self):
        self.assertEqual(allocate(0,[],[]), {'confirmed':[],'waitlist':[],'remaining':0})
        self.assertEqual(allocate(0,[{'id':'x','seats':1}],[]), {'confirmed':[],'waitlist':['x'],'remaining':0})
        self.assertEqual(allocate(7,[{'id':'x','seats':8}],['x']), {'confirmed':[],'waitlist':[],'remaining':7})
    def test_invalid(self):
        for capacity in [True,False,-1,1.0,None,'2']:
            with self.subTest(capacity=capacity), self.assertRaises(ValueError): allocate(capacity,[],[])
        for value in [None,{},(), 'a']:
            with self.subTest(value=value), self.assertRaises(ValueError): allocate(3,value,[])
            with self.subTest(value=value), self.assertRaises(ValueError): allocate(3,[],value)
        for req in [None,{}, {'id':'','seats':1}, {'id':[],'seats':1}, {'id':'x','seats':0},
                    {'id':'x','seats':True}, {'id':'x','seats':1.0}, {'id':'x','seats':-1},
                    {'id':'x','seats':1,'extra':0}]:
            with self.subTest(req=req), self.assertRaises(ValueError): allocate(3,[req],[])
        for value in ['',1,None,[]]:
            with self.subTest(value=value), self.assertRaises(ValueError): allocate(3,[],[value])
    def test_no_mutation(self):
        req=[{'id':'a','seats':1}]; cancelled=['other']; before=copy.deepcopy((req,cancelled))
        result=allocate(2,req,cancelled); result['confirmed'].append('changed'); result['waitlist'].append('x')
        self.assertEqual((req,cancelled),before)
        bad=req+[{'id':'bad','seats':0}]; before=copy.deepcopy(bad)
        with self.assertRaises(ValueError): allocate(2,bad,[])
        self.assertEqual(bad,before)
    def test_capacity_conservation(self):
        req=[{'id':str(i),'seats':i+1} for i in range(8)]
        for capacity in range(40):
            result=allocate(capacity,req,[])
            ids=result['confirmed']+result['waitlist']
            self.assertEqual(ids,[r['id'] for r in req])
            used=sum(int(i)+1 for i in result['confirmed'])
            self.assertEqual(used+result['remaining'],capacity)
            self.assertGreaterEqual(result['remaining'],0)
''',
    },
    {
        'id': 'virtual-wallet', 'family': 'function-school.virtual-wallet',
        'brief': '''Implement settle(initial_balance, operations) in solution.py for
fictional game credits, no real money. initial_balance is a nonnegative int,
never bool. operations is a list of dicts with exactly id (nonempty str) and
delta (any integer, including zero, never bool). Process first occurrences in
order. Same id and same delta is an idempotent retry: do not apply it again and
do not add a history row. Same id with different delta raises ValueError.
Balance must never become negative at ANY intermediate step; a later credit
does not excuse an earlier overdraft. Return exactly {"balance": int,
"history": [{"id": str, "delta": int, "balance": int}, ...]}, one new row per
unique operation showing its immediate resulting balance. Use integer arithmetic
of arbitrary precision, never float. Validate inputs; any invalid input or
overdraft raises ValueError. Never mutate inputs on success/failure; returned
structures must not alias input structures. Empty operations is valid.''',
        'lessons': {
            'test_retry_after_debit': 'Check request identity before applying a repeated debit; exact retries must neither debit nor append history again.',
            'test_intermediate_overdraft': 'Check funds at every unique operation, not just at the final balance after later credits.',
            'test_large_integer_balance': 'Keep credit arithmetic integral throughout; floating point loses precision for large integer balances.',
        },
        'tests': '''import copy
import unittest
from solution import settle

class Checks(unittest.TestCase):
    def test_retry_after_debit(self):
        self.assertEqual(settle(7,[{'id':'a','delta':-7},{'id':'a','delta':-7},{'id':'b','delta':3},{'id':'z','delta':0}]),
            {'balance':3,'history':[{'id':'a','delta':-7,'balance':0},{'id':'b','delta':3,'balance':3},{'id':'z','delta':0,'balance':3}]})
    def test_conflicting_id(self):
        with self.assertRaises(ValueError): settle(100,[{'id':'x','delta':1},{'id':'x','delta':2}])
    def test_intermediate_overdraft(self):
        with self.assertRaises(ValueError): settle(2,[{'id':'a','delta':-3},{'id':'b','delta':50}])
    def test_large_integer_balance(self):
        large=10**40+17
        result=settle(large,[{'id':'x','delta':-13}])
        self.assertEqual(result,{'balance':large-13,'history':[{'id':'x','delta':-13,'balance':large-13}]})
        self.assertIs(type(result['balance']),int)
    def test_empty(self):
        self.assertEqual(settle(0,[]),{'balance':0,'history':[]})
    def test_invalid(self):
        for initial in [True,False,-1,1.0,None,'2']:
            with self.subTest(initial=initial), self.assertRaises(ValueError): settle(initial,[])
        for value in [None,{},(), 'a']:
            with self.subTest(value=value), self.assertRaises(ValueError): settle(3,value)
        for op in [None,{}, {'id':'','delta':1}, {'id':[],'delta':1}, {'id':1,'delta':1},
                   {'id':'x','delta':True}, {'id':'x','delta':False}, {'id':'x','delta':1.0},
                   {'id':'x','delta':None}, {'id':'x','delta':1,'extra':0}]:
            with self.subTest(op=op), self.assertRaises(ValueError): settle(3,[op])
    def test_no_mutation(self):
        ops=[{'id':'x','delta':1}]; before=copy.deepcopy(ops); result=settle(3,ops)
        result['history'][0]['delta']=999; self.assertEqual(ops,before)
        bad=ops+[{'id':'bad','delta':-99}]; before=copy.deepcopy(bad)
        with self.assertRaises(ValueError): settle(3,bad)
        self.assertEqual(bad,before)
    def test_replay_and_conservation(self):
        ops=[{'id':str(i),'delta':i-4} for i in range(12)]
        result=settle(20,ops); replay=settle(20,ops+ops)
        self.assertEqual(result,replay)
        self.assertEqual(result['balance'],20+sum(op['delta'] for op in ops))
        self.assertEqual(len(result['history']),len(ops))
        for index,row in enumerate(result['history']):
            self.assertEqual(row['balance'],20+sum(op['delta'] for op in ops[:index+1]))
''',
    },
]
