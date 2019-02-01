import os
import sys
import time
import gym
import tensorflow as tf
import multiprocessing

from importlib import import_module
from baselines import bench, logger
from baselines.common import set_global_seeds
from baselines.ppo2 import ppo2
from baselines.common.vec_env.dummy_vec_env import DummyVecEnv

try:
    from mpi4py import MPI
except ImportError:
    MPI = None

ncpu = multiprocessing.cpu_count()

if sys.platform == 'darwin':
    ncpu //= 2

config = tf.ConfigProto(allow_soft_placement=True,
                        intra_op_parallelism_threads=ncpu,
                        inter_op_parallelism_threads=ncpu,
                        log_device_placement=False)

config.gpu_options.allow_growth = True

tf.Session(config=config).__enter__()

def get_alg_module(alg, submodule=None):
    submodule = submodule or alg
    try:
        # first try to import the alg module from baselines
        alg_module = import_module('.'.join(['baselines', alg, submodule]))
    except ImportError:
        # then from rl_algs
        alg_module = import_module('.'.join(['rl_' + 'algs', alg, submodule]))

    return alg_module

def get_learn_function(alg, submodule=None):
    return get_alg_module(alg, submodule).learn

def get_learn_function_defaults(alg, env_type):
    try:
        alg_defaults = get_alg_module(alg, 'defaults')
        kwargs = getattr(alg_defaults, env_type)()
    except (ImportError, AttributeError):
        kwargs = {}
    return kwargs

def make_env():
    env = gym.make(alg_kwargs['env_name'])
    env = bench.Monitor(env, logger.get_dir() and os.path.join(logger.get_dir()), allow_early_resets=True)

    return env

env_type = 'mara_mlp'
alg_kwargs = get_learn_function_defaults('ppo2', env_type)

logdir = '/tmp/ros_rl2/' + alg_kwargs['env_name'] + '/ppo2/'
logger.configure( os.path.abspath(logdir) )

format_strs = os.getenv('MARA_LOG_FORMAT', 'stdout,log,csv,tensorboard').split(',')
logger.configure(os.path.abspath(logdir), format_strs)


with open(logger.get_dir() + "/parameters.txt", 'w') as out:
    out.write(
        'num_layers = ' + str(alg_kwargs['num_layers']) + '\n'
        + 'num_hidden = ' + str(alg_kwargs['num_hidden']) + '\n'
        + 'layer_norm = ' + str(alg_kwargs['layer_norm']) + '\n'
        + 'nsteps = ' + str(alg_kwargs['nsteps']) + '\n'
        + 'nminibatches = ' + str(alg_kwargs['nminibatches']) + '\n'
        + 'lam = ' + str(alg_kwargs['lam']) + '\n'
        + 'gamma = ' + str(alg_kwargs['gamma']) + '\n'
        + 'noptepochs = ' + str(alg_kwargs['noptepochs']) + '\n'
        + 'log_interval = ' + str(alg_kwargs['log_interval']) + '\n'
        + 'ent_coef = ' + str(alg_kwargs['ent_coef']) + '\n'
        + 'cliprange = ' + str(alg_kwargs['cliprange']) + '\n'
        + 'vf_coef = ' + str(alg_kwargs['vf_coef']) + '\n'
        + 'max_grad_norm = ' + str(alg_kwargs['max_grad_norm']) + '\n'
        + 'seed = ' + str(alg_kwargs['seed']) + '\n'
        + 'value_network = ' + alg_kwargs['value_network'] + '\n'
        + 'network = ' + alg_kwargs['network'] + '\n'
        + 'total_timesteps = ' + str(alg_kwargs['total_timesteps']) + '\n'
        + 'save_interval = ' + str(alg_kwargs['save_interval']) + '\n'
        + 'env_name = ' + alg_kwargs['env_name'] )

env = DummyVecEnv([make_env])

learn = get_learn_function('ppo2')
set_global_seeds(alg_kwargs['seed'])
rank = MPI.COMM_WORLD.Get_rank() if MPI else 0

alg_kwargs.pop('env_name')

# Do transfer learning
#load_path = ''
#model = learn(env=env,load_path= load_path, **alg_kwargs)

# Do not do transfer learning
model = learn(env=env, **alg_kwargs)