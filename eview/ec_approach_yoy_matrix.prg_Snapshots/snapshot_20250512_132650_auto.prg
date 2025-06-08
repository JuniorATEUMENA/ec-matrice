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

cd "C:\Users\fbinp\Documents\Cergy\M1 Data Economie et Transition\capstone"

%wf0="data_es_eurostat_1999q1_2024q4"

wfopen %wf0
%pays = "es"  
WFCREATE(wf=data_trimmed_mat_yoy_{%startdate}_{%endate}_{%pays}_,page=quarterly_{%pays}) q %startdate %endsmpl
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


scalar nsim=1000
scalar w =20  ' 5-year projections

	for %var {%groups}
	matrix(nsim,5) ann_{%var} 'matrices for 4 shocks annualized + tx_moy
	next
	matrix(nsim,5) ann_ratio 'matrices for 4 shocks annualized + tx_moy

rndseed 123456
!j=1
while !j<=nsim
	rndseed 123456+{!j}'   
    matrix epsn = @rmvnorm(cov,w)
    mtos(epsn,g_eps)

'4) Annualize the shocks

	for %var {%groups}
	series acc_eps_{%var} = @cumsum(eps_{%var})
	stom(acc_eps_{%var},acc_{%var} )
		!i=1 ' first year shocks initialization
		matrix ann_{%var}(!j,!i) = acc_{%var}(1,4*!i)  
		matrix ann_ltn_10y(!j,!i) = acc_{%var}(1,4*!i)*!i/maturity_{%pays}     

		!i=2
		while !i<=5
		matrix ann_{%var}(!j,!i) = acc_{%var}(1,4*!i)  -  acc_{%var}(1,4*(!i-1)) 'keeps the 4 quarters of year !i only
		matrix ann_ltn_10y(!j,!i) = acc_{%var}(1,4*!i)*!i/maturity_{%pays}   'ltn_10y's special treatment: shocks cumulate over 5 years

		!i = !i+1
		wend
	next
	!j=!j+1
wend

'5) copy the shocks' matrices in an annual page
pagecreate(page=annual_{%pays}) a %startsim0m1 %endsmpl

		copy quarterly_{%pays}\ann_soldep_p
		copy quarterly_{%pays}\ann_stn_3m      
		copy quarterly_{%pays}\ann_ltn_10y 
		copy quarterly_{%pays}\ann_g_v_yoy
		copy quarterly_{%pays}\nsim
wfopen %wf0 

wfselect data_trimmed_mat_yoy_{%startdate}_{%endate}_{%pays}_
pageselect annual_{%pays}
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

'on opère des ajustements sur les variables pour garder la cohérence des ordres de grandeurs pour tous les scénarios

''on opère des ajustements sur les variables pour garder la cohérence des ordres de grandeurs pour tous les scénarios
series dette_iir_bkcom_000_{%pays} = dette_bkcom_000_{%pays}/100
series soldep_p_bkcom_000_{%pays}= soldep_p_bkcom_000_{%pays}/100
series g_v_yoy_bkcom_000_{%pays}= g_v_yoy_bkcom_000_{%pays}/100
series ltn_10y_bkcom_000_{%pays}= ltn_10y_bkcom_000_{%pays}/100
series stn_3m_bkcom_000_{%pays}= stn_3m_bkcom_000_{%pays}/100
series tx_moy_bkcom_000_{%pays}= tx_moy_bkcom_000_{%pays}/100


smpl %endate %endate 
scalar dettem1 = dette_iir_bkcom_000_{%pays} 

smpl %startsim0 %endsim 

'group for baseline trajectories
group g_base soldep_p_bkcom_000_{%pays}  stn_3m_bkcom_000_{%pays} ltn_10y_bkcom_000_{%pays} g_v_yoy_bkcom_000_{%pays} tx_moy_bkcom_000_{%pays} 
stom(g_base,base_m)

%groups2 = "soldep_p stn_3m ltn_10y g_v_yoy tx_moy dette_iir "
for %var {%groups2}
	matrix(nsim,5) sim_{%var} 'matrices for shocked baseline
next

!j=1
while !j<=nsim
 			!k=1 'projection year
			while !k<=5
				sim_soldep_p(!j,!k) = base_m(!k,1)+ann_soldep_p(!j,!k) 
				sim_stn_3m(!j,!k) = base_m(!k,2)+ann_stn_3m(!j,!k)
				sim_ltn_10y(!j,!k) = base_m(!k,3)+ann_ltn_10y(!j,!k)
				sim_g_v_yoy(!j,!k) = base_m(!k,4)+ann_g_v_yoy(!j,!k) 
				sim_tx_moy(!j,!k) =  (base_m(!k,5)+alphalt_{%pays}*ann_ltn_10y(!j,!k)+alphact_{%pays}*ann_stn_3m(!j,!k))*(base_m(!k,5)+alphalt_{%pays}*ann_ltn_10y(!j,!k)+alphact_{%pays}*ann_stn_3m(!j,!k)>0) 'positivity constraint
			!k=!k+1
			wend
	!j=!j+1
wend

' debt ratio and prob computation

!j=1
while !j<=nsim
	sim_dette_iir(!j,1)=dettem1*((1+sim_tx_moy(!j,1))/(1+sim_g_v_yoy(!j,1))) -sim_soldep_p(!j,1) 
 			!k=2 'projection year
			while !k<=5
			sim_dette_iir(!j,!k)=sim_dette_iir(!j,!k-1)*((1+sim_tx_moy(!j,!k))/(1+sim_g_v_yoy(!j,!k))) -sim_soldep_p(!j,!k) 
			  
			!k=!k+1
			wend
	!j=!j+1
wend

for %var {%groups2}
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
smpl %startsim0+1 %endsim
	for %var {%groups2}
 		for %vec {%vector}
 		mtos({%vec}_{%var}, {%vec}s_{%var}_s)
 		next
	next
smpl %startsim0 %startsim0
	for %var {%groups2}
 		for %vec {%vector}
		series {%vec}s_{%var}_s = {%var}_bkcom_000_{%pays}
		series dette_iir_bkcom_000_{%pays} = dette_iir_bkcom_000_{%pays}
 		next
	next
smpl %startsim0 %endsim
for %var {%groups2}
	group g_fan_chart_{%var}_{%pays}  q95s_{%var}_s q5s_{%var}_s q90s_{%var}_s q10s_{%var}_s q80s_{%var}_s q20s_{%var}_s q70s_{%var}_s q30s_{%var}_s q60s_{%var}_s q40s_{%var}_s meds_{%var}_s {%var}_bkcom_000_{%pays}
	freeze(fan_boot_{%var}_{%pays} ) g_fan_chart_{%var}_{%pays}.mixed band(1,2,3,4,5,6,7,8,9,10) line(11,12)
	fan_boot_{%var}_{%pays}.legend columns(2)
	fan_boot_{%var}_{%pays}.setelem(1) fillcolor(@rgb(185,185,255))
	fan_boot_{%var}_{%pays}.setelem(2) fillcolor(@rgb(136,136,255))
	fan_boot_{%var}_{%pays}.setelem(3) fillcolor(@rgb(66,66,255))
	fan_boot_{%var}_{%pays}.setelem(4) fillcolor(@rgb(33,33,255))
	fan_boot_{%var}_{%pays}.setelem(4) fillcolor(@rgb(20,20,255))
	fan_boot_{%var}_{%pays}.setelem(1) lcolor(black)  'médiane
	fan_boot_{%var}_{%pays}.setelem(2) lcolor(red) '
	fan_boot_{%var}_{%pays}.setelem(11) legend("Median")
	fan_boot_{%var}_{%pays}.setelem(12) legend({%var} bkcom)
next



