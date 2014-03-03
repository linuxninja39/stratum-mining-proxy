from twisted.internet import reactor

from stratum.event_handler import GenericEventHandler
from jobs import Job
import utils
import version as _version

import stratum_listener

import stratum.logger


#new import
from twisted.internet import reactor, defer
from stratum.socket_transport import SocketTransportFactory
from mining_libs.custom_classes import CustomSocketTransportClientFactory as SocketTransportClientFactory
from stratum.services import ServiceEventHandler
# from twisted.web.server import Site
#
# from mining_libs import stratum_listener
# from mining_libs import getwork_listener
from mining_libs import jobs
from mining_libs import worker_registry
from mining_libs import multicast_responder
from mining_libs import version
from mining_libs import utils

#end new import

log = stratum.logger.get_logger('proxy')

class ClientMiningService(GenericEventHandler):
    job_registry = None  # Reference to JobRegistry instance
    timeout = None  # Reference to IReactorTime object
    switched = False
    cp = None  # Reference to CustomSocketClientTransportFactory

    @classmethod
    def reset_timeout(cls):
        if cls.timeout != None:
            if not cls.timeout.called:
                cls.timeout.cancel()
            cls.timeout = None

        cls.timeout = reactor.callLater(2*60, cls.on_timeout)

    @classmethod
    def on_timeout(cls):
        '''
            Try to reconnect to the pool after two minutes of no activity on the connection.
            It will also drop all Stratum connections to sub-miners
            to indicate connection issues.
        '''
        log.error("Connection to upstream pool timed out")
        cls.reset_timeout()
        cls.job_registry.f.reconnect()

    @classmethod
    def set_cp(cls, cp):
        cls.cp = cp



    def handle_event(self, method, params, connection_ref):
        '''Handle RPC calls and notifications from the pool'''

        # Yay, we received something from the pool,
        # let's restart the timeout.
        self.reset_timeout()
        # log.warning('Current method %s' % method )
        log.info(connection_ref.transport.getPeer().host)
        log.info(connection_ref.transport.getPeer().port)
        log.info(params)
        if self.cp:
            self.cp.get_ip()
        if method == 'mining.notify':
            '''Proxy just received information about new mining job'''

            (job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, clean_jobs) = params[:9]
            #print len(str(params)), len(merkle_branch)

            '''
            log.debug("Received new job #%s" % job_id)
            log.debug("prevhash = %s" % prevhash)
            log.debug("version = %s" % version)
            log.debug("nbits = %s" % nbits)
            log.debug("ntime = %s" % ntime)
            log.debug("clean_jobs = %s" % clean_jobs)
            log.debug("coinb1 = %s" % coinb1)
            log.debug("coinb2 = %s" % coinb2)
            log.debug("merkle_branch = %s" % merkle_branch)
            '''

            # Broadcast to Stratum clients
            stratum_listener.MiningSubscription.on_template(
                            job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, clean_jobs)

            # Broadcast to getwork clients
            job = Job.build_from_broadcast(job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime)
            log.info("New job %s for prevhash %s, clean_jobs=%s" % \
                 (job.job_id, utils.format_hash(job.prevhash), clean_jobs))

            self.job_registry.add_template(job, clean_jobs)



        elif method == 'mining.set_difficulty':
            difficulty = params[0]
            log.info("Setting new difficulty: %s" % difficulty)

            stratum_listener.DifficultySubscription.on_new_difficulty(difficulty)
            self.job_registry.set_difficulty(difficulty)

        elif method == 'client.reconnect':
            (hostname, port, wait) = params[:3]
            new = list(self.job_registry.f.main_host[::])
            if hostname: new[0] = hostname
            if port: new[1] = port

            log.info("Server asked us to reconnect to %s:%d" % tuple(new))
            self.job_registry.f.reconnect(new[0], new[1], wait)

        elif method == 'client.add_peers':
            '''New peers which can be used on connection failure'''
            return False
            '''
            peerlist = params[0] # TODO
            for peer in peerlist:
                self.job_registry.f.add_peer(peer)
            return True
            '''
        elif method == 'client.get_version':
            return "stratum-proxy/%s" % _version.VERSION

        elif method == 'client.show_message':

            # Displays message from the server to the terminal
            utils.show_message(params[0])
            return True

        elif method == 'mining.get_hashrate':
            return {} # TODO

        elif method == 'mining.get_temperature':
            return {} # TODO

        elif method == 'mining.proxy_switch':
            (host, port) = params[:2]
            log.info('Switching to new proxy')
            log.warning("Trying to connect to Stratum pool at %s:%d" % (host, port))
            stratum_listener.StratumProxyService._new_switch_proxy(host, port)
            log.info('Switching to new proxy finished')

        else:
            '''Pool just asked us for something which we don't support...'''
            log.error("Unhandled method %s with params %s" % (method, params))

