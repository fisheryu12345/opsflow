# -*- coding: utf-8 -*-
"""Workflow Validator tests — 12 validation rules for ITSM workflow structure."""
from django.test import SimpleTestCase
from itsm.services.workflow_validator import validate_workflow


def _state(key, name, stype):
    return (key, {'id': hash(key) % 10000, 'node_key': key, 'name': name, 'type': stype})


def _trans(tid, from_key, to_key, condition='', name='', condition_type=''):
    return (tid, {
        'id': tid, 'name': name,
        'from_node_key': from_key, 'to_node_key': to_key,
        'condition': condition, 'condition_type': condition_type or ('script' if condition else ''),
    })


def _make_states(*args):
    return dict([_state(*a) for a in args])


def _make_trans(*args):
    return dict([_trans(*a) for a in args])


class TestValidSimpleFlow(SimpleTestCase):
    """Normal START → NORMAL → END flow should pass all checks."""

    def test_simple_linear(self):
        states = _make_states(
            ('start', 'Start', 'START'),
            ('fill', 'Fill Form', 'NORMAL'),
            ('end', 'End', 'END'),
        )
        trans = _make_trans(
            ('t1', 'start', 'fill'),
            ('t2', 'fill', 'end'),
        )
        result = validate_workflow(states, trans)
        self.assertTrue(result['valid'], msg=f"Errors: {[c for c in result['checks'] if c['status']=='fail']}")
        # All should pass
        for c in result['checks']:
            self.assertEqual(c['status'], 'pass', msg=f"{c['rule']}: {c['message']}")


class TestMissingStartEnd(SimpleTestCase):
    """E1: Must have START and END nodes."""

    def test_missing_start(self):
        states = _make_states(('fill', 'Fill', 'NORMAL'), ('end', 'End', 'END'))
        trans = _make_trans(('t1', 'fill', 'end'))
        result = validate_workflow(states, trans)
        self.assertFalse(result['valid'])
        fails = [c for c in result['checks'] if c['status'] == 'fail' and c['rule'] == 'start_end_exist']
        self.assertTrue(any('START' in c['message'] for c in fails))

    def test_missing_end(self):
        states = _make_states(('start', 'Start', 'START'), ('fill', 'Fill', 'NORMAL'))
        trans = _make_trans(('t1', 'start', 'fill'))
        result = validate_workflow(states, trans)
        self.assertFalse(result['valid'])
        fails = [c for c in result['checks'] if c['status'] == 'fail' and c['rule'] == 'start_end_exist']
        self.assertTrue(any('END' in c['message'] for c in fails))

    def test_missing_both(self):
        states = _make_states(('a', 'A', 'NORMAL'), ('b', 'B', 'NORMAL'))
        trans = _make_trans(('t1', 'a', 'b'))
        result = validate_workflow(states, trans)
        self.assertFalse(result['valid'])
        fails = [c for c in result['checks'] if c['status'] == 'fail' and c['rule'] == 'start_end_exist']
        self.assertEqual(len(fails), 2)


class TestCycleDetection(SimpleTestCase):
    """E2: DAG cycle detection via Kahn."""

    def test_simple_cycle(self):
        states = _make_states(
            ('start', 'Start', 'START'),
            ('a', 'A', 'APPROVAL'),
            ('b', 'B', 'APPROVAL'),
            ('end', 'End', 'END'),
        )
        trans = _make_trans(
            ('t1', 'start', 'a'),
            ('t2', 'a', 'b'),
            ('t3', 'b', 'a'),  # cycle: a→b→a
            ('t4', 'b', 'end'),
        )
        result = validate_workflow(states, trans)
        self.assertFalse(result['valid'])
        self.assertTrue(any(c['rule'] == 'dag_no_cycle' and c['status'] == 'fail'
                            for c in result['checks']))

    def test_no_cycle(self):
        states = _make_states(
            ('start', 'Start', 'START'),
            ('a', 'A', 'APPROVAL'),
            ('end', 'End', 'END'),
        )
        trans = _make_trans(('t1', 'start', 'a'), ('t2', 'a', 'end'))
        result = validate_workflow(states, trans)
        dag_check = [c for c in result['checks'] if c['rule'] == 'dag_no_cycle']
        self.assertEqual(dag_check[0]['status'], 'pass')


class TestTransitionRefsValid(SimpleTestCase):
    """E3: Transition from/to must reference existing states."""

    def test_invalid_from(self):
        states = _make_states(('start', 'Start', 'START'), ('end', 'End', 'END'))
        trans = _make_trans(('t1', 'start', 'end'), ('t2', 'ghost', 'end'))
        result = validate_workflow(states, trans)
        self.assertFalse(result['valid'])
        self.assertTrue(any('ghost' in c['message'] for c in result['checks']
                            if c['rule'] == 'transition_refs_valid' and c['status'] == 'fail'))

    def test_invalid_to(self):
        states = _make_states(('start', 'Start', 'START'), ('end', 'End', 'END'))
        trans = _make_trans(('t1', 'start', 'ghost'))
        result = validate_workflow(states, trans)
        self.assertFalse(result['valid'])
        self.assertTrue(any('ghost' in c['message'] for c in result['checks']
                            if c['rule'] == 'transition_refs_valid' and c['status'] == 'fail'))


class TestExclusiveGateway(SimpleTestCase):
    """E4: min edges, E5: conditions."""

    def test_too_few_edges(self):
        states = _make_states(
            ('start', 'Start', 'START'),
            ('gw', 'Gateway', 'EXCLUSIVE'),
            ('end', 'End', 'END'),
        )
        trans = _make_trans(('t1', 'start', 'gw'), ('t2', 'gw', 'end'))
        result = validate_workflow(states, trans)
        self.assertFalse(result['valid'])
        self.assertTrue(any(c['rule'] == 'exclusive_gateway_min_edges' and c['status'] == 'fail'
                            for c in result['checks']))

    def test_missing_all_conditions(self):
        states = _make_states(
            ('start', 'Start', 'START'),
            ('gw', 'Gateway', 'EXCLUSIVE'),
            ('a', 'Approve', 'APPROVAL'),
            ('b', 'Reject', 'APPROVAL'),
            ('end', 'End', 'END'),
        )
        trans = _make_trans(
            ('t1', 'start', 'gw'),
            ('t2', 'gw', 'a', ''),   # no condition
            ('t3', 'gw', 'b', ''),   # no condition
            ('t4', 'a', 'end'),
            ('t5', 'b', 'end'),
        )
        result = validate_workflow(states, trans)
        self.assertFalse(result['valid'])
        self.assertTrue(any(c['rule'] == 'exclusive_gateway_conditions' and c['status'] == 'fail'
                            for c in result['checks']))

    def test_one_condition_ok(self):
        """At least N-1 conditions = valid."""
        states = _make_states(
            ('start', 'Start', 'START'),
            ('gw', 'Gateway', 'EXCLUSIVE'),
            ('a', 'A', 'APPROVAL'),
            ('b', 'B', 'APPROVAL'),
            ('end', 'End', 'END'),
        )
        trans = _make_trans(
            ('t1', 'start', 'gw'),
            ('t2', 'gw', 'a', '${fill.amount} > 1000'),
            ('t3', 'gw', 'b', ''),  # default branch, ok
            ('t4', 'a', 'end'),
            ('t5', 'b', 'end'),
        )
        result = validate_workflow(states, trans)
        # Should be valid (E5 passes because 1 of 2 has condition)
        # But might fail other checks; just check E5 passes
        e5 = [c for c in result['checks'] if c['rule'] == 'exclusive_gateway_conditions']
        if e5:
            self.assertNotEqual(e5[0]['status'], 'fail',
                                msg=f"E5 should pass: {e5[0]['message']}")


class TestConditionalParallel(SimpleTestCase):
    """E6: Every CONDITIONAL_PARALLEL edge must have condition."""

    def test_missing_condition(self):
        states = _make_states(
            ('start', 'Start', 'START'),
            ('gw', 'Gateway', 'CONDITIONAL_PARALLEL'),
            ('a', 'A', 'TASK'),
            ('b', 'B', 'TASK'),
            ('end', 'End', 'END'),
        )
        trans = _make_trans(
            ('t1', 'start', 'gw'),
            ('t2', 'gw', 'a', '${n1.f} > 0'),
            ('t3', 'gw', 'b', ''),  # missing condition
        )
        result = validate_workflow(states, trans)
        self.assertFalse(result['valid'])
        self.assertTrue(any(c['rule'] == 'conditional_parallel_conditions' and c['status'] == 'fail'
                            for c in result['checks']))


class TestConvergeGateway(SimpleTestCase):
    """E7: Converge must have >= 2 incoming edges."""

    def test_single_incoming(self):
        states = _make_states(
            ('start', 'Start', 'START'),
            ('a', 'A', 'TASK'),
            ('conv', 'Converge', 'COVERAGE'),
            ('end', 'End', 'END'),
        )
        trans = _make_trans(
            ('t1', 'start', 'a'),
            ('t2', 'a', 'conv'),
            ('t3', 'conv', 'end'),
        )
        result = validate_workflow(states, trans)
        self.assertFalse(result['valid'])
        self.assertTrue(any(c['rule'] == 'converge_gateway_min_in' and c['status'] == 'fail'
                            for c in result['checks']))


class TestDuplicateNodeKey(SimpleTestCase):
    """E8: No duplicate node_keys."""

    def test_duplicate(self):
        states = {
            'dup1': {'id': 1, 'node_key': 'dup', 'name': 'Node A', 'type': 'NORMAL'},
            'dup2': {'id': 2, 'node_key': 'dup', 'name': 'Node B', 'type': 'NORMAL'},
        }
        result = validate_workflow(states, {})
        self.assertFalse(result['valid'])
        self.assertTrue(any(c['rule'] == 'duplicate_node_key' and c['status'] == 'fail'
                            for c in result['checks']))


class TestOrphanNodes(SimpleTestCase):
    """E9: Non-START/END nodes must have in-degree and out-degree."""

    def test_no_incoming(self):
        states = _make_states(
            ('start', 'Start', 'START'),
            ('orphan', 'Orphan', 'NORMAL'),
            ('end', 'End', 'END'),
        )
        trans = _make_trans(('t1', 'start', 'end'))
        result = validate_workflow(states, trans)
        self.assertFalse(result['valid'])
        self.assertTrue(any(c['rule'] == 'orphan_nodes' and c['status'] == 'fail'
                            and '入边' in c['message'] for c in result['checks']))

    def test_no_outgoing(self):
        states = _make_states(
            ('start', 'Start', 'START'),
            ('orphan', 'Orphan', 'NORMAL'),
            ('end', 'End', 'END'),
        )
        trans = _make_trans(('t1', 'start', 'orphan'))
        result = validate_workflow(states, trans)
        self.assertFalse(result['valid'])
        self.assertTrue(any(c['rule'] == 'orphan_nodes' and c['status'] == 'fail'
                            and '出边' in c['message'] for c in result['checks']))


class TestUnreachableNodes(SimpleTestCase):
    """E10: All nodes must be reachable from START."""

    def test_unreachable(self):
        states = _make_states(
            ('start', 'Start', 'START'),
            ('a', 'A', 'NORMAL'),
            ('ghost', 'Ghost', 'NORMAL'),
            ('end', 'End', 'END'),
        )
        trans = _make_trans(('t1', 'start', 'a'), ('t2', 'a', 'end'))
        result = validate_workflow(states, trans)
        self.assertFalse(result['valid'])
        self.assertTrue(any(c['rule'] == 'unreachable_nodes' and c['status'] == 'fail'
                            and 'ghost' in c['message'] for c in result['checks']))


class TestDeadEndPaths(SimpleTestCase):
    """E11: Non-END nodes must have out-degree >= 1."""

    def test_dead_end(self):
        states = _make_states(
            ('start', 'Start', 'START'),
            ('dead', 'Dead End', 'APPROVAL'),
            ('end', 'End', 'END'),
        )
        trans = _make_trans(('t1', 'start', 'dead'))
        result = validate_workflow(states, trans)
        self.assertFalse(result['valid'])
        self.assertTrue(any(c['rule'] == 'dead_end_paths' and c['status'] == 'fail'
                            for c in result['checks']))


class TestConditionInvalidSyntax(SimpleTestCase):
    """E12: Unsupported operators in condition expressions."""

    def test_contains_operator(self):
        states = _make_states(
            ('start', 'Start', 'START'),
            ('gw', 'Gateway', 'EXCLUSIVE'),
            ('a', 'A', 'APPROVAL'),
            ('b', 'B', 'APPROVAL'),
            ('end', 'End', 'END'),
        )
        trans = _make_trans(
            ('t1', 'start', 'gw'),
            ('t2', 'gw', 'a', '${n1.reason} contains urgent'),
            ('t3', 'gw', 'b', '${n1.amount} > 1000'),
            ('t4', 'a', 'end'),
            ('t5', 'b', 'end'),
        )
        result = validate_workflow(states, trans)
        self.assertFalse(result['valid'])
        self.assertTrue(any(c['rule'] == 'condition_invalid_syntax' and c['status'] == 'fail'
                            for c in result['checks']))

    def test_valid_operators(self):
        states = _make_states(
            ('start', 'Start', 'START'),
            ('gw', 'Gateway', 'EXCLUSIVE'),
            ('a', 'A', 'APPROVAL'),
            ('b', 'B', 'APPROVAL'),
            ('end', 'End', 'END'),
        )
        trans = _make_trans(
            ('t1', 'start', 'gw'),
            ('t2', 'gw', 'a', '${n1.field} in ["x","y"]'),
            ('t3', 'gw', 'b', '${n1.field} notin ["z"]'),
            ('t4', 'a', 'end'),
            ('t5', 'b', 'end'),
        )
        result = validate_workflow(states, trans)
        # E12 should pass for valid operators
        e12 = [c for c in result['checks'] if c['rule'] == 'condition_invalid_syntax']
        if e12:
            self.assertEqual(e12[0]['status'], 'pass',
                             msg=f"E12 should pass: {e12[0]['message']}")

    def test_starts_with(self):
        states = _make_states(
            ('start', 'Start', 'START'), ('gw', 'G', 'EXCLUSIVE'),
            ('a', 'A', 'APPROVAL'), ('end', 'End', 'END'),
        )
        trans = _make_trans(
            ('t1', 'start', 'gw'),
            ('t2', 'gw', 'a', '${n1.name} startsWith PROD'),
            ('t3', 'gw', 'end', ''),
            ('t4', 'a', 'end'),
        )
        result = validate_workflow(states, trans)
        self.assertFalse(result['valid'])
        self.assertTrue(any(c['rule'] == 'condition_invalid_syntax' and c['status'] == 'fail'
                            for c in result['checks']))


class TestProcessorCheck(SimpleTestCase):
    """E13: APPROVAL/SIGN nodes must have processors configured."""

    def test_missing_processors(self):
        """PERSON type with empty processors should fail."""
        states = _make_states(
            ('start', 'Start', 'START'),
            ('approval', 'Approval', 'APPROVAL'),
            ('end', 'End', 'END'),
        )
        states['approval']['processors'] = ''
        states['approval']['processors_type'] = 'PERSON'
        trans = _make_trans(('t1', 'start', 'approval'), ('t2', 'approval', 'end'))
        result = validate_workflow(states, trans)
        self.assertFalse(result['valid'])
        self.assertTrue(any(c['rule'] == 'processor_check' and c['status'] == 'fail'
                            for c in result['checks']))

    def test_empty_processors_type_should_fail(self):
        """No processor type selected at all should fail."""
        states = _make_states(
            ('start', 'Start', 'START'),
            ('approval', 'Approval', 'APPROVAL'),
            ('end', 'End', 'END'),
        )
        states['approval']['processors'] = ''
        states['approval']['processors_type'] = ''
        trans = _make_trans(('t1', 'start', 'approval'), ('t2', 'approval', 'end'))
        result = validate_workflow(states, trans)
        self.assertFalse(result['valid'])
        self.assertTrue(any(c['rule'] == 'processor_check' and c['status'] == 'fail'
                            for c in result['checks']))

    def test_starter_type_ok(self):
        """STARTER type with empty processors is valid — auto-resolved at runtime."""
        states = _make_states(
            ('start', 'Start', 'START'),
            ('approval', 'Approval', 'APPROVAL'),
            ('end', 'End', 'END'),
        )
        states['approval']['processors'] = ''
        states['approval']['processors_type'] = 'STARTER'
        trans = _make_trans(('t1', 'start', 'approval'), ('t2', 'approval', 'end'))
        result = validate_workflow(states, trans)
        e13 = [c for c in result['checks'] if c['rule'] == 'processor_check']
        if e13:
            self.assertEqual(e13[0]['status'], 'pass',
                             msg=f"E13 should pass for STARTER: {e13[0]['message']}")

    def test_has_processors(self):
        states = _make_states(
            ('start', 'Start', 'START'),
            ('approval', 'Approval', 'APPROVAL'),
            ('end', 'End', 'END'),
        )
        states['approval']['processors'] = '[{"id":1,"name":"admin"}]'
        states['approval']['processors_type'] = 'PERSON'
        trans = _make_trans(('t1', 'start', 'approval'), ('t2', 'approval', 'end'))
        result = validate_workflow(states, trans)
        e13 = [c for c in result['checks'] if c['rule'] == 'processor_check']
        if e13:
            self.assertEqual(e13[0]['status'], 'pass',
                             msg=f"E13 should pass: {e13[0]['message']}")


class TestGatewayBalance(SimpleTestCase):
    """E14: Fork gateways must have matching converge gateways."""

    def test_fork_join_mismatch(self):
        states = _make_states(
            ('start', 'Start', 'START'),
            ('pg1', 'P1', 'PARALLEL'),
            ('pg2', 'P2', 'PARALLEL'),
            ('cg', 'C', 'COVERAGE'),
            ('end', 'End', 'END'),
        )
        trans = _make_trans(
            ('t1', 'start', 'pg1'),
            ('t2', 'pg1', 'cg'),
            ('t3', 'pg2', 'cg'),
            ('t4', 'cg', 'end'),
        )
        result = validate_workflow(states, trans)
        self.assertFalse(result['valid'])
        self.assertTrue(any(c['rule'] == 'gw_balance' and c['status'] == 'fail'
                            for c in result['checks']))

    def test_fork_join_balanced(self):
        states = _make_states(
            ('start', 'Start', 'START'),
            ('pg', 'P', 'PARALLEL'),
            ('cg', 'C', 'COVERAGE'),
            ('end', 'End', 'END'),
        )
        trans = _make_trans(
            ('t1', 'start', 'pg'),
            ('t2', 'pg', 'cg'),
            ('t3', 'cg', 'end'),
        )
        result = validate_workflow(states, trans)
        e14 = [c for c in result['checks'] if c['rule'] == 'gw_balance']
        if e14:
            self.assertEqual(e14[0]['status'], 'pass',
                             msg=f"E14 should pass: {e14[0]['message']}")
