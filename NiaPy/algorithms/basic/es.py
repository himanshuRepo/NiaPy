# encoding=utf8
# pylint: disable=mixed-indentation, trailing-whitespace, multiple-statements, attribute-defined-outside-init, logging-not-lazy, unused-argument, singleton-comparison, no-else-return, line-too-long, arguments-differ, no-self-use, superfluous-parens, redefined-builtin, bad-continuation, unused-variable
import logging
from math import ceil
from numpy import argmin, argsort, log, sum, fmax, sqrt, full, exp, eye, diag, apply_along_axis, round, any, asarray, dot, random as rand, tile, inf, where
from numpy.linalg import norm, cholesky as chol, eig, solve, lstsq
from NiaPy.algorithms.algorithm import Algorithm, Individual

logging.basicConfig()
logger = logging.getLogger('NiaPy.algorithms.basic')
logger.setLevel('INFO')

__all__ = ['EvolutionStrategy1p1', 'EvolutionStrategyMp1', 'EvolutionStrategyMpL', 'EvolutionStrategyML', 'CovarianceMaatrixAdaptionEvolutionStrategy']

class IndividualES(Individual):
	def __init__(self, **kwargs):
		task, x, rho = kwargs.get('task', None), kwargs.get('x', None), kwargs.get('rho', 1)
		if rho != None: self.rho = rho
		elif task != None or x != None: self.rho = 1.0
		Individual.__init__(self, **kwargs)

class EvolutionStrategy1p1(Algorithm):
	r"""Implementation of (1 + 1) evolution strategy algorithm. Uses just one individual.

	**Algorithm:** (1 + 1) Evolution Strategy Algorithm

	**Date:** 2018

	**Authors:** Klemen Berkovič

	**License:** MIT

	**Reference URL:**

	**Reference paper:**
	"""
	Name = ['EvolutionStrategy1p1', 'EvolutionStrategy(1+1)', 'ES(1+1)']

	@staticmethod
	def typeParameters(): return {
			'mu': lambda x: isinstance(x, int) and x > 0,
			'k': lambda x: isinstance(x, int) and x > 0,
			'c_a': lambda x: isinstance(x, (float, int)) and x > 1,
			'c_r': lambda x: isinstance(x, (float, int)) and 0 < x < 1,
			'epsilon': lambda x: isinstance(x, float) and 0 < x < 1
	}

	def setParameters(self, mu=1, k=10, c_a=1.1, c_r=0.5, epsilon=1e-20, **ukwargs):
		r"""Set the arguments of an algorithm.

		**Arguments:**

		mu {integer} -- Number of parents

		k {integer} -- Number of iterations before checking and fixing rho

		c_a {real} -- Search range amplification factor

		c_r {real} -- Search range reduction factor
		"""
		self.mu, self.k, self.c_a, self.c_r, self.epsilon = mu, k, c_a, c_r, epsilon
		if ukwargs: logger.info('Unused arguments: %s' % (ukwargs))

	def mutate(self, x, rho): return x + self.normal(0, rho, len(x))

	def updateRho(self, rho, k):
		phi = k / self.k
		if phi < 0.2: return self.c_r * rho if rho > self.epsilon else 1
		elif phi > 0.2: return self.c_a * rho if rho > self.epsilon else 1
		else: return rho

	def runTask(self, task):
		c, ki = IndividualES(task=task, rand=self.Rand), 0
		while not task.stopCondI():
			if task.Iters % self.k == 0: c.rho, ki = self.updateRho(c.rho, ki), 0
			cn = [task.repair(self.mutate(c.x, c.rho), self.Rand) for _i in range(self.mu)]
			cn_f = [task.eval(cn[i]) for i in range(self.mu)]
			ib = argmin(cn_f)
			if cn_f[ib] < c.f: c.x, c.f, ki = cn[ib], cn_f[ib], ki + 1
		return c.x, c.f

class EvolutionStrategyMp1(EvolutionStrategy1p1):
	r"""Implementation of (mu + 1) evolution strategy algorithm. Algorithm creates mu mutants but into new generation goes only one individual.

	**Algorithm:** ($\mu$ + 1) Evolution Strategy Algorithm

	**Date:** 2018

	**Authors:** Klemen Berkovič

	**License:** MIT

	**Reference URL:**

	**Reference paper:**
	"""
	Name = ['EvolutionStrategyMp1', 'EvolutionStrategy(mu+1)', 'ES(m+1)']

	def setParameters(self, **kwargs):
		mu = kwargs.pop('mu', 40)
		EvolutionStrategy1p1.setParameters(self, mu=mu, **kwargs)

class EvolutionStrategyMpL(EvolutionStrategy1p1):
	r"""Implementation of (mu + lambda) evolution strategy algorithm. Mulation creates lambda individual. Lambda individual compete with mu individuals for survival, so only mu individual go to new generation.

	**Algorithm:** ($mu$ + $lambda$) Evolution Strategy Algorithm

	**Date:** 2018

	**Authors:** Klemen Berkovič

	**License:** MIT

	**Reference URL:**

	**Reference paper:**
	"""
	Name = ['EvolutionStrategyMpL', 'EvolutionStrategy(mu+lambda)', 'ES(m+l)']

	@staticmethod
	def typeParameters():
		d = EvolutionStrategy1p1.typeParameters()
		d['lam'] = lambda x: isinstance(x, int) and x > 0
		return d

	def setParameters(self, lam=45, **ukwargs):
		r"""Set the arguments of an algorithm.

		**Arguments:**

		lam {integer} -- Number of new individual generated by mutation
		"""
		EvolutionStrategy1p1.setParameters(self, **ukwargs)
		self.lam = lam
		if ukwargs: logger.info('Unused arguments: %s' % (ukwargs))

	def mutate(self, x, rho): return x + self.normal(0, rho, len(x))

	def updateRho(self, pop, k):
		phi = k / self.k
		if phi < 0.2:
			for i in pop: i.rho = self.c_r * i.rho
		elif phi > 0.2:
			for i in pop: i.rho = self.c_a * i.rho

	def changeCount(self, a, b):
		k = 0
		for e in b:
			if e not in a: k += 1
		return k

	def mutateRepair(self, pop, task):
		i = self.randint(self.mu)
		return task.repair(self.mutate(pop[i].x, pop[i].rho), rnd=self.Rand)

	def runTask(self, task):
		c, ki = [IndividualES(task=task, rand=self.Rand) for _i in range(self.mu)], 0
		while not task.stopCondI():
			if task.Iters % self.k == 0: _, ki = self.updateRho(c, ki), 0
			cm = [self.mutateRepair(c, task) for i in range(self.lam)]
			cn = [IndividualES(x=cm[i], task=task, rand=self.Rand) for i in range(self.lam)]
			cn.extend(c)
			cn = [cn[i] for i in argsort([i.f for i in cn])[:self.mu]]
			ki += self.changeCount(c, cn)
			c = cn
		return c[0].x, c[0].f

class EvolutionStrategyML(EvolutionStrategyMpL):
	r"""Implementation of (mu, lambda) evolution strategy algorithm. Algorithm is good for dynamic environments. Mu individual create lambda chields. Only best mu chields go to new generation. Mu parents are discarded.

	**Algorithm:** ($mu$ + $lambda$) Evolution Strategy Algorithm

	**Date:** 2018

	**Authors:** Klemen Berkovič

	**License:** MIT

	**Reference URL:**

	**Reference paper:**
	"""
	Name = ['EvolutionStrategyML', 'EvolutionStrategy(mu,lambda)', 'ES(m,l)']

	def newPop(self, pop):
		pop_s = argsort([i.f for i in pop])
		if self.mu < self.lam: return [pop[i] for i in pop_s[:self.mu]]
		npop = list()
		for i in range(int(ceil(float(self.mu) / self.lam))): npop.extend(pop[:self.lam if (self.mu - i * self.lam) >= self.lam else self.mu - i * self.lam])
		return npop

	def runTask(self, task):
		c = [IndividualES(task=task, rand=self.Rand) for _i in range(self.mu)]
		while not task.stopCondI():
			cm = [self.mutateRepair(c, task) for i in range(self.lam)]
			cn = [IndividualES(x=cm[i], task=task, rand=self.Rand) for i in range(self.lam)]
			c = self.newPop(cn)
		return c[0].x, c[0].f

def CovarianceMaatrixAdaptionEvolutionStrategyF(task, epsilon=1e-20, rnd=rand):
	lam, alpha_mu, hs, sigma0 = (4 + round(3 * log(task.D))) * 10, 2, 0, 0.3 * task.bcRange()
	mu = int(round(lam / 2))
	w = log(mu + 0.5) - log(range(1, mu + 1))
	w = w / sum(w)
	mueff = 1 / sum(w ** 2)
	cs = (mueff + 2) / (task.D + mueff + 5)
	ds = 1 + cs + 2 * max(sqrt((mueff - 1) / (task.D + 1)) - 1, 0)
	ENN = sqrt(task.D) * (1 - 1 / (4 * task.D) + 1 / (21 * task.D ** 2))
	cc, c1 = (4 + mueff / task.D) / (4 + task.D + 2 * mueff / task.D), 2 / ((task.D + 1.3) ** 2 + mueff)
	cmu, hth = min(1 - c1, alpha_mu * (mueff - 2 + 1 / mueff) / ((task.D + 2) ** 2 + alpha_mu * mueff / 2)), (1.4 + 2 / (task.D + 1)) * ENN
	ps, pc, C, sigma, M = full(task.D, 0.0), full(task.D, 0.0), eye(task.D), sigma0, full(task.D, 0.0)
	x = rnd.uniform(task.bcLower(), task.bcUpper())
	x_f = task.eval(x)
	while not task.stopCondI():
		pop_step = asarray([rnd.multivariate_normal(full(task.D, 0.0), C) for _ in range(int(lam))])
		pop = asarray([task.repair(x + sigma * ps, rnd) for ps in pop_step])
		pop_f = apply_along_axis(task.eval, 1, pop)
		isort = argsort(pop_f)
		pop, pop_f, pop_step = pop[isort[:mu]], pop_f[isort[:mu]], pop_step[isort[:mu]]
		if pop_f[0] < x_f: x, x_f = pop[0], pop_f[0]
		M = sum(w * pop_step.T, axis=1)
		ps = solve(chol(C).conj() + epsilon, ((1 - cs) * ps + sqrt(cs * (2 - cs) * mueff) * M + epsilon).T)[0].T
		sigma *= exp(cs / ds * (norm(ps) / ENN - 1)) ** 0.3
		ifix = where(sigma == inf)
		if any(ifix): sigma[ifix] = sigma0
		if norm(ps) / sqrt(1 - (1 - cs) ** (2 * (task.Iters + 1))) < hth: hs = 1
		else: hs = 0
		delta = (1 - hs) * cc * (2 - cc)
		pc = (1 - cc) * pc + hs * sqrt(cc * (2 - cc) * mueff) * M
		C = (1 - c1 - cmu) * C + c1 * (tile(pc, [len(pc), 1]) * tile(pc.reshape([len(pc), 1]), [1, len(pc)]) + delta * C)
		for i in range(mu): C += cmu * w[i] * tile(pop_step[i], [len(pop_step[i]), 1]) * tile(pop_step[i].reshape([len(pop_step[i]), 1]), [1, len(pop_step[i])])
		E, V = eig(C)
		if any(E < epsilon):
			E = fmax(E, 0)
			C = lstsq(V.T, dot(V, diag(E)).T, rcond=None)[0].T
	return x, x_f

class CovarianceMaatrixAdaptionEvolutionStrategy(Algorithm):
	r"""Implementation of (mu, lambda) evolution strategy algorithm. Algorithm is good for dynamic environments. Mu individual create lambda chields. Only best mu chields go to new generation. Mu parents are discarded.

	**Algorithm:** ($mu$ + $lambda$) Evolution Strategy Algorithm

	**Date:** 2018

	**Authors:** Klemen Berkovič

	**License:** MIT

	**Reference URL:** https://arxiv.org/abs/1604.00772

	**Reference paper:** Hansen, Nikolaus. "The CMA evolution strategy: A tutorial." arXiv preprint arXiv:1604.00772 (2016).
	"""
	Name = ['CovarianceMaatrixAdaptionEvolutionStrategy', 'CMA-ES', 'CMAES']

	@staticmethod
	def typeParameters(): return {
			'epsilon': lambda x: isinstance(x, (float, int)) and 0 < x < 1
	}

	def setParameters(self, epsilon=1e-20, **ukwargs):
		self.epsilon = epsilon
		if ukwargs: logger.info('Unused arguments: %s' % (ukwargs))

	def runTask(self, task): return CovarianceMaatrixAdaptionEvolutionStrategyF(task, self.epsilon, rnd=self.Rand)

# vim: tabstop=3 noexpandtab shiftwidth=3 softtabstop=3