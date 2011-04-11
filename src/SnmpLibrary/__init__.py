#
# Kontron SnmpLibrary
#
# author: Michael Walle <michael.walle@kontron.com>
#

import os.path

from pysnmp.smi import builder
from pysnmp.entity import engine
from pysnmp.entity.rfc3413.oneliner import cmdgen
from pyasn1.type import univ
from pysnmp.proto import rfc1902

class _SnmpConnection:
    pass

def try_int(i):
    try:
        return int(i)
    except ValueError:
        return i

class SnmpLibrary:
    AGENT_NAME = 'robotframework agent'
    def __init__(self):
        e = engine.SnmpEngine()
        self._snmp_engine = e
        self._builder = e.msgAndPduDsp.mibInstrumController.mibBuilder
        self._host = None

    def set_host(self, host, port=161):
        self._host = host
        self._port = port

    def set_community_string(self, community):
        self._community = community

    def add_mib_search_path(self, path):
        """Adds a path to the MIB search path.

        Example:
        | Add MIB Search Path | /usr/share/mibs/ |
        """

        self._info('Adding MIB path %s' % path)
        if not os.path.exists(path):
            raise RuntimeError('Path "%s" does not exist' % path)

        paths = self._builder.getMibPath()
        paths += (path, )
        self._debug('New paths: %s' % ' '.join(paths))
        self._builder.setMibPath(*paths)

    def preload_mibs(self, *names):
        """Preloads MIBs.

        Preloading MIBs can be useful in cases where the `Get`- or
        `Set`-keyword should be executed as fast as possible.

        `names` can either be a list of MIB names or can be empty in which case
        all available MIBs are preloaded.

        This keyword should be used within the test setup.

        Note: Preloading all MIBs take a long time.
        """
        if len(names):
            self._info('Preloading MIBs %s' % ' '.join(list(names)))
        else:
            self._info('Preloading all available MIBs')
        self._builder.loadModules(*names)

    def _parse_oid(self, oid):
        # The following notations are possible:
        #   SNMPv2-MIB::sysDescr.0
        #   .1.3.6.1.2.1.1.1.0
        #   .iso.org.6.internet.2.1.1.1.0
        #   sysDescr.0
        if '::' in oid:
            mib, sym = oid.split('::', 1)
            oid = None
        elif oid.startswith('.'):
            oid = map(try_int, oid[1:].split('.'))
            oid = tuple(oid)
        else:
            mib = ''
            sym = oid
            oid = None

        if oid is None:
            sym, suffixes = sym.split('.', 1)
            suffixes = suffixes.split('.')
            suffixes = map(try_int, suffixes)
            suffixes = tuple(suffixes)
            oid = ((mib, sym),) + suffixes

        return oid

    def get(self, oid):
        """Does a SNMP GET request.

        Examples:
        | Get | SNMPv2-MIB::sysDescr.0 |
        | Get | .1.3.6.1.2.1.1.1.0 |
        | Get | .iso.org.6.internet.2.1.1.1.0 |
        | Get | sysDescr.0 |
        """

        if not self._host:
            raise RuntimeError('No host set')

        oid = self._parse_oid(oid)

        error_indication, error_status, _, var = \
                cmdgen.CommandGenerator(self._snmp_engine).getCmd(
                cmdgen.CommunityData(self.AGENT_NAME, self._community),
                cmdgen.UdpTransportTarget((self._host, self._port)), oid
        )

        if error_indication is not Null:
            raise RuntimeError('SNMP GET failed: %s' % error_indication
        if error_status != 0:
            raise RuntimeError('SNMP GET failed: %s' %
                error_status.prettyPrint())

        oid, obj = var[0]

        if obj == univ.Null(''):
            raise RuntimeError('Object with OID ".%s" not found' %
                    '.'.join(map(str, oid)))

        return obj.prettyOut(obj)

    def set(self, oid, value):
        """Does a SNMP GET request.

        See `Get` for more information on possible OID notations.

        Automatic converting to the SNMP type expected by the remote system is
        only supported for OIDs for which there is a MIB describing it. If you
        want to use an OID which is not described by a MIB, you'll have to use
        the `Set XXX`-keyword or `Convert To XXX`-keyword.

        Example:
        | Set | SNMPv2::sysDescr.0 | New System Description |
        """

        oid = self._parse_oid(oid)

        #from pysnmp.proto import rfc1902
        #value = rfc1902.OctetString(value)

        _, error, _, var = cmdgen.CommandGenerator(self._snmp_engine).setCmd(
                cmdgen.CommunityData(self.AGENT_NAME, self._community),
                cmdgen.UdpTransportTarget((self._host, 161)), (oid, value)
        )

        if error != 0:
            raise RuntimeError('SNMP SET failed: %s' % error.prettyPrint())

    def convert_to_octetstring(self, value):
        """Converts a value to a SNMP OctetString object."""
        return rfc1902.OctetString(value)

    def convert_to_integer(self, value):
        """Converts a value to a SNMP Integer object."""
        return rfc1902.Integer(value)

    def convert_to_integer32(self, value):
        """Converts a value to a SNMP Integer32 object."""
        return rfc1902.Integer32(value)

    def convert_to_counter32(self, value):
        """Converts a value to a SNMP Counter32 object."""
        return rfc1902.Counter32(value)

    def convert_to_counter64(self, value):
        """Converts a value to a SNMP Counter64 object."""
        return rfc1902.Counter64(value)

    def convert_to_gauge32(self, value):
        """Converts a value to a SNMP Gauge32 object."""
        return rfc1902.Gauge32(value)

    def convert_to_unsigned32(self, value):
        """Converts a value to a SNMP Unsigned32 object."""
        return rfc1902.Unsigned32(value)

    def convert_to_timeticks(self, value):
        """Converts a value to a SNMP TimeTicks object."""
        return rfc1902.TimeTicks(value)

    def set_octetstring(self, value):
        """Does a SNMP SET request after converting the value to an
        OctetString SNMP Object.

        This is a convenient keyword, it does the same as a `Convert To
        OctetString` followed by a `Set`.
        """

        value = self.convert_to_octetstring(value)
        self.set(oid, value)

    def set_integer(self, oid, value):
        """Does a SNMP SET request after converting the value to an
        Integer SNMP Object.

        This is a convenient keyword, it does the same as a `Convert To
        Integer` followed by a `Set`.
        """

        value = self.convert_to_integer(value)
        self.set(oid, value)

    def set_integer32(self, oid, value):
        """Does a SNMP SET request after converting the value to an
        Integer32 SNMP Object.

        See also `Set Integer`.
        """

        value = self.convert_to_integer32(value)
        self.set(oid, value)

    def set_counter32(self, oid, value):
        """Does a SNMP SET request after converting the value to a
        Counter32 SNMP Object.

        See also `Set Integer`.
        """

        value = self.convert_to_counter32(value)
        self.set(oid, value)

    def set_counter64(self, oid, value):
        """Does a SNMP SET request after converting the value to a
        Counter64 SNMP Object.

        See also `Set Integer`.
        """

        value = self.convert_to_counter64(value)
        self.set(oid, value)

    def set_gauge32(self, oid, value):
        """Does a SNMP SET request after converting the value to a
        Gauge32 SNMP Object.

        See also `Set Integer`.
        """

        value = self.convert_to_gauge32(value)
        self.set(oid, value)

    def set_unsigned32(self, oid, value):
        """Does a SNMP SET request after converting the value to a
        Unsigned32 SNMP Object.

        See also `Set Integer`.
        """

        value = self.convert_to_unsigned32(value)
        self.set(oid, value)

    def set_timeticks(self, oid, value):
        """Does a SNMP SET request after converting the value to a
        TimeTicks SNMP Object.

        See also `Set Integer`.
        """

        value = self.convert_to_timeticks(value)
        self.set(oid, value)

    def _warn(self, msg):
        self._log(msg, 'WARN')

    def _info(self, msg):
        self._log(msg, 'INFO')

    def _debug(self, msg):
        self._log(msg, 'DEBUG')

    def _log(self, msg, level=None):
        self._is_valid_log_level(level, raise_if_invalid=True)
        msg = msg.strip()
        if level is None:
            level = self._default_log_level
        if msg != '':
            print '*%s* %s' % (level.upper(), msg)

    def _is_valid_log_level(self, level, raise_if_invalid=False):
        if level is None:
            return True
        if isinstance(level, basestring) and \
                level.upper() in ['TRACE', 'DEBUG', 'INFO', 'WARN', 'HTML']:
            return True
        if not raise_if_invalid:
            return False
        raise RuntimeError("Invalid log level '%s'" % level)


if __name__ == "__main__":
    s = SnmpLibrary()
    s.set_host('10.0.111.112')
    s.set_community_string('private')
    s.preload_mibs('SNMPv2-MIB')
    #s.load_mibs()
    #print s.get((1,3,6,1,2,1,1,1,0))
    #print s.get((('SNMPv2-MIB', 'sysDescr'), 0))
    #print s.get(('SNMPv2-MIB', ''))
    #print s.get('SNMPv2-MIB::sysDescr.0')
    #print s.get('sysDescr.0')
    #print s.get('.1.3.6.1.2.1.1.1.1')
    #s.set('.iso.org.6.internet.2.1.1.1.0', 'test')
    print s.get('.1.3.6.1.2.1.1.1.0')
    s.set('.1.3.6.1.2.1.1.6.0', 'Test')
    print s.get('SNMPv2-MIB::sysLocation.0')
    #print s.get('KEX-MCG-MIB::clkRefValid.1.1')
    print s.get('.1.3.6.1.4.1.15000.5.2.1.0')
    #s.set('.1.3.6.1.4.1.15000.5.2.1.0', Gauge32(200))
    s.set_gauge32('.1.3.6.1.4.1.15000.5.2.1.0', '200')
    print s.get('.1.3.6.1.4.1.15000.5.2.1.0')

