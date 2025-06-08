mode quiet

%startdate = "1999q4"
%endsmpl = "2045q4"
%endate = "2023q4"  '<<<<<<<<<<<<<<<< fin observations trim
%startsim0m1 = "2021" '<<<<<<<<<<<<<<<< année fin observations et debut fancharts - 2

%startsim0 = "2023" '<<<<<<<<<<<<<<<< année fin observations et debut fancharts
%startsim1 = "2024" '<<<<<<<<<<<<<<<< année début projection
%endsim = "2028q4" '<<<<<<<<<<<<<<<< fin projections trim
%endadjust = "2028" '<<<<<<<<<<<<<<<<<fin période d'ajustement
%endeval = "2033" '<<<<<<<<<<<<<<<<< five years after %endadjust
'

cd "C:\Users\junio\Documents\M1 DATA Semester2\Capstone\ultime"

%wf0="data_es_eurostat_1999q1_2024q4"

wfopen %wf0
%pays = "es"    ' 
WFCREATE(wf=data_trimmed_yoy_{%startdate}_{%endate}_{%pays}_,page=quarterly_{%pays}) q %startdate %endsmpl
smpl %startdate %endate


      copy(c=na) %wf0::source\soldep_p_{%pays}
      copy(c=na) %wf0::source\stn_3m_{%pays}
      copy(c=na) %wf0::source\ltn_10y_{%pays}
      copy(c=na) %wf0::source\g_v_yoy_{%pays}
      copy(c=na) %wf0::source\maturity_{%pays}

wfclose %wf0

'1) Winsorize the series as the EC does : 5 and 95 pct quantiles since 1999q4

%groups="soldep_p stn_3m ltn_10y g_v_yoy"
	for %var {%groups}
	scalar q95_{%var} = @quantile({%var}_{%pays},0.95)
	scalar q5_{%var}= @quantile({%var}_{%pays},0.05)
	series {%var}_trimmed ={%var}_{%pays}*@between({%var}_{%pays},q5_{%var},q95_{%var})+ q5_{%var}*({%var}_{%pays}< q5_{%var}) + q95_{%var}*({%var}_{%pays}> q95_{%var}) 
	next

series stn_3m_trimmed = stn_3m_trimmed/100
series  ltn_10y_trimmed =  ltn_10y_trimmed/100

'2) Built the "historical shocks" and compute their covariance matrix

	for %var {%groups}
	series shock_hist_{%var} =d({%var}_trimmed)
	next

smpl %startdate+1 %endate  'starting in 2000Q1

group shock_hist shock_hist_soldep_p shock_hist_stn_3m shock_hist_ltn_10y shock_hist_g_v_yoy 
stom(shock_hist,shock_hist_m)
sym cov = @covs(shock_hist_m)  'd.o.f. corrected

'3) 10,000 random draws  
smpl %endate+1 %endsim
series  eps_soldep_p   
series  eps_stn_3m
series eps_ltn_10y
series eps_g_v_yoy
group g_eps eps_soldep_p eps_stn_3m eps_ltn_10y eps_g_v_yoy

tic
scalar nsim=1000
scalar w =20  ' 5-year projections


pagecreate(page=annual_{%pays}) a %startsim0m1 %endsmpl
pageselect quarterly_{%pays}
rndseed 123456
!j=1
while !j<=nsim
' 
	smpl %endate+1 %endsim
  
	series  eps_soldep_p_{!j}   
	series  eps_stn_3m_{!j}
	series eps_ltn_10y_{!j}
	series eps_g_v_yoy_{!j}

	group g_eps_{!j} eps_soldep_p_{!j} eps_stn_3m_{!j} eps_ltn_10y_{!j} eps_g_v_yoy_{!j} 
	rndseed 123456+{!j}
     matrix epsn = @rmvnorm(cov,w)
     mtos(epsn,g_eps_{!j})
	pageselect annual_{%pays}
	smpl %endate+1 %endsim
	
		copy(c=s) quarterly_{%pays}\eps_soldep_p_{!j}
		copy(c=s) quarterly_{%pays}\eps_stn_3m_{!j}      
		copy(c=s) quarterly_{%pays}\eps_ltn_10y_{!j} 
		copy(c=s) quarterly_{%pays}\eps_g_v_yoy_{!j}
		copy quarterly_{%pays}\maturity_{%pays}

		series acc_eps_ltn_10y_{!j} = @cumsum(eps_ltn_10y_{!j}) 
			!k=0
			while !k<=4
			smpl %startsim1+!k  %startsim1+!k
			series eps_ltn_10y_{!j} = acc_eps_ltn_10y_{!j} *(!k+1)/maturity_{%pays}  'years before average maturity if projection > 5 years
			!k=!k+1
  			wend
	pageselect quarterly_{%pays}
	!j=!j+1
wend

pageselect annual_{%pays}

smpl %startsim0 %endsmpl
	copy quarterly_{%pays}\nsim
wfopen %wf0 

wfselect data_trimmed_yoy_{%startdate}_{%endate}_{%pays}_
pageselect annual_{%pays}
smpl %startsim0m1 %endsmpl

      copy %wf0::annual\mal_p_bkcom_000_{%pays} dette_bkcom_000_{%pays}
      copy %wf0::annual\dda_bkcom_000_{%pays} *  'source : https://economy-finance.ec.europa.eu/economic-and-fiscal-governance/stability-and-growth-pact
	 copy %wf0::annual\g_v_yoy_bkcom_000_{%pays} *
	 copy %wf0::annual\soldep_p_bkcom_000_{%pays} *
	 copy %wf0::annual\ltn_10y_bkcom_000_{%pays} *
	 copy %wf0::annual\stn_3m_bkcom_000_{%pays} *
      copy %wf0::annual\iir_bkcom_000_{%pays} tx_moy_bkcom_000_{%pays}
	 copy %wf0::annual\alphact_{%pays} *
	 copy %wf0::annual\alphalt_{%pays} *
wfclose %wf0
'
''on opère des ajustements sur les variables pour garder la cohérence des ordres de grandeurs pour tous les scénarios
series dette_bkcom_000_{%pays} = dette_bkcom_000_{%pays}/100
series soldep_p_bkcom_000_{%pays}= soldep_p_bkcom_000_{%pays}/100
series g_v_yoy_bkcom_000_{%pays}= g_v_yoy_bkcom_000_{%pays}/100
series ltn_10y_bkcom_000_{%pays}= ltn_10y_bkcom_000_{%pays}/100
series stn_3m_bkcom_000_{%pays}= stn_3m_bkcom_000_{%pays}/100
series tx_moy_bkcom_000_{%pays}= tx_moy_bkcom_000_{%pays}/100

smpl %endate %endate 
scalar dettem1 = dette_bkcom_000_{%pays} 

smpl %startsim0 %endsim 

'group for baseline trajectories
group g_base soldep_p_bkcom_000_{%pays}  stn_3m_bkcom_000_{%pays} ltn_10y_bkcom_000_{%pays} g_v_yoy_bkcom_000_{%pays} tx_moy_bkcom_000_{%pays} 
group dette_iir ' pour la dette
group g_v_yoy ' pour le taux de croissance du pib
group stn_3m ' pour le taux à 3m
group ltn_10y 'pour le taux à 10 ans
group tx_moy  'pour le taux moyen (calculé comme part CT*tx à 3m et part LT*taux à 10 ans)
group soldep_p 'pour le solde primaire

!j=1
while !j<=nsim
			smpl %startsim0 %startsim0
			series sim_dette_iir_{!j} = dette_bkcom_000_{%pays}
			smpl %startsim1 %endsim
				series sim_soldep_p_{!j} = soldep_p_bkcom_000_{%pays}+eps_soldep_p_{!j} 
				series sim_stn_3m_{!j} = stn_3m_bkcom_000_{%pays} +eps_stn_3m_{!j} 
				series sim_ltn_10y_{!j} = ltn_10y_bkcom_000_{%pays} +eps_ltn_10y_{!j} 
				series sim_g_v_yoy_{!j} = g_v_yoy_bkcom_000_{%pays} +eps_g_v_yoy_{!j} 
				'EC shares of ST and LT debt shares:
				series sim_tx_moy_{!j} = (tx_moy_bkcom_000_{%pays} +alphalt_{%pays}*eps_ltn_10y_{!j}+alphact_{%pays}*eps_stn_3m_{!j})*(tx_moy_bkcom_000_{%pays} +alphalt_{%pays}*eps_ltn_10y_{!j}+alphact_{%pays}*eps_stn_3m_{!j}>0)       'positivity constraint on the average rate
				series sim_dette_iir_{!j} =  sim_dette_iir_{!j}(-1)*((1+sim_tx_moy_{!j})/(1+sim_g_v_yoy_{!j})) -sim_soldep_p_{!j}+dda_bkcom_000_{%pays}/100 
				dette_iir.add sim_dette_iir_{!j}
				g_v_yoy.add  sim_g_v_yoy_{!j}
				stn_3m.add sim_stn_3m_{!j} 
				ltn_10y.add sim_ltn_10y_{!j} 
				tx_moy.add sim_tx_moy_{!j}
				soldep_p.add sim_soldep_p_{!j} 
!j=!j+1
wend

'Probability that debt ratio in T+5 > debt ratio in T

'matrix(5,nsim) dette_iir_m
vector(nsim) prob_m
stom(dette_iir,dette_iir_m)
!j=1
while !j<=nsim
	vector prob_m(!j) = (dette_iir_m(5,!j)>dettem1)  'prob debt 2028 > 2023
	vector prob_s = @csum(prob_m)
	scalar prob = prob_s/nsim
	!j=!j+1
wend

%groups2="soldep_p stn_3m ltn_10y g_v_yoy tx_moy dette_iir"

for %var {%groups2}
	stom({%var},sim_{%var})
	matrix sim_{%var} = @transpose(sim_{%var})

	vector q5_{%var} = @cquantile(sim_{%var}, .05)
	vector q10_{%var} = @cquantile(sim_{%var}, .1)
	vector q20_{%var} = @cquantile(sim_{%var}, .2)
	vector q30_{%var} = @cquantile(sim_{%var}, .3)
	vector q40_{%var} = @cquantile(sim_{%var}, .4)
	vector med_{%var} = @cquantile(sim_{%var}, .5)
	vector q60_{%var} = @cquantile(sim_{%var}, .6)
	vector q70_{%var} = @cquantile(sim_{%var}, .7)
	vector q80_{%var} = @cquantile(sim_{%var}, .8)
	vector q90_{%var} = @cquantile(sim_{%var}, .9)
	vector q95_{%var} = @cquantile(sim_{%var}, .95)
next

%vector="q95 q5 q90 q10 q80 q20 q70 q30 q60 q40 med"

	for %var {%groups2}
 		for %vec {%vector}
 		mtos({%vec}_{%var}, {%vec}s_{%var}_s)
 		next
	next
series conewidth = q90s_dette_iir_s - q10s_dette_iir_s
series dette_iir_bkcom_000_{%pays} = dette_bkcom_000_{%pays}

smpl %startsim0 %startsim0
	for %var {%groups2}
 		for %vec {%vector}
		series {%vec}s_{%var}_s = {%var}_bkcom_000_{%pays}
		series dette_iir_bkcom_000_{%pays} = dette_bkcom_000_{%pays}
 		next
	next

smpl %startsim0 %endsim
for %var {%groups2}
	group g_fan_chart_{%var}_{%scena} q95s_{%var}_s q5s_{%var}_s q90s_{%var}_s q10s_{%var}_s q80s_{%var}_s q20s_{%var}_s q70s_{%var}_s q30s_{%var}_s q60s_{%var}_s q40s_{%var}_s meds_{%var}_s {%var}_bkcom_000_{%pays}
	freeze(fan_boot_{%var}_{%scena}) g_fan_chart_{%var}_{%scena}.mixed band(1,2,3,4,5,6,7,8,9,10) line(11,12)
	fan_boot_{%var}_{%scena}.legend columns(4)
	fan_boot_{%var}_{%scena}.setelem(1) fillcolor(@rgb(185,185,255))
	fan_boot_{%var}_{%scena}.setelem(2) fillcolor(@rgb(136,136,255))
	fan_boot_{%var}_{%scena}.setelem(3) fillcolor(@rgb(66,66,255))
	fan_boot_{%var}_{%scena}.setelem(4) fillcolor(@rgb(33,33,255))
	fan_boot_{%var}_{%scena}.setelem(4) fillcolor(@rgb(20,20,255))
	fan_boot_{%var}_{%scena}.setelem(1) lcolor(black)  'médiane
	fan_boot_{%var}_{%scena}.setelem(2) lcolor(red) '
	fan_boot_{%var}_{%scena}.setelem(3) linecolor(@rgb(255,128,64))
	fan_boot_{%var}_{%scena}.setelem(1) legend("q95")
	fan_boot_{%var}_{%scena}.setelem(2) legend("q5")
	fan_boot_{%var}_{%scena}.setelem(3) legend("q90")
	fan_boot_{%var}_{%scena}.setelem(4) legend("q10")
	fan_boot_{%var}_{%scena}.setelem(5) legend("q80")
	fan_boot_{%var}_{%scena}.setelem(6) legend("q20")
	fan_boot_{%var}_{%scena}.setelem(7) legend("q70")
	fan_boot_{%var}_{%scena}.setelem(8) legend("q30")
	fan_boot_{%var}_{%scena}.setelem(9) legend("q60")
	fan_boot_{%var}_{%scena}.setelem(10) legend("q40")
	fan_boot_{%var}_{%scena}.setelem(11) legend("Median")
	fan_boot_{%var}_{%scena}.setelem(12) legend({%var}_{%pays} (DSA))
next

toc

pageselect quarterly_{%pays}
delete eps_g_v_yoy_*
delete eps_ltn_10y_*
delete eps_stn_3m_*
delete eps_soldep_p_*
delete eps_g_v_yoy_*
delete g_eps_*
pageselect annual_{%pays}
delete acc_eps*
delete eps_*
delete sim_*


