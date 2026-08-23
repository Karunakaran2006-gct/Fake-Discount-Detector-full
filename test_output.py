import pandas as pd
import io
from fdd.features import extract_features
from fdd.detection import analyze
from fdd.explain import generate_explanation

csv_data = """date,product_name,price
2026-02-16,Nike Air Max,8031
2026-02-16,Sony Headphones,4974
2026-02-16,Dabur Honey 1kg,445
2026-02-16,Basmati Rice 5kg,600
2026-02-17,Nike Air Max,7981
2026-02-17,Sony Headphones,4988
2026-02-17,Dabur Honey 1kg,447
2026-02-17,Basmati Rice 5kg,602
2026-02-18,Nike Air Max,8036
2026-02-18,Sony Headphones,5029
2026-02-18,Dabur Honey 1kg,446
2026-02-18,Basmati Rice 5kg,603
2026-02-19,Nike Air Max,7954
2026-02-19,Sony Headphones,4963
2026-02-19,Dabur Honey 1kg,446
2026-02-19,Basmati Rice 5kg,604
2026-02-20,Nike Air Max,8014
2026-02-20,Sony Headphones,5037
2026-02-20,Dabur Honey 1kg,445
2026-02-20,Basmati Rice 5kg,606
2026-02-21,Nike Air Max,8041
2026-02-21,Sony Headphones,5029
2026-02-21,Dabur Honey 1kg,451
2026-02-21,Basmati Rice 5kg,607
2026-02-22,Nike Air Max,8025
2026-02-22,Sony Headphones,4995
2026-02-22,Dabur Honey 1kg,445
2026-02-22,Basmati Rice 5kg,609
2026-02-23,Nike Air Max,7970
2026-02-23,Sony Headphones,5014
2026-02-23,Dabur Honey 1kg,450
2026-02-23,Basmati Rice 5kg,610
2026-02-24,Nike Air Max,7977
2026-02-24,Sony Headphones,5003
2026-02-24,Dabur Honey 1kg,446
2026-02-24,Basmati Rice 5kg,611
2026-02-25,Nike Air Max,7962
2026-02-25,Sony Headphones,5005
2026-02-25,Dabur Honey 1kg,450
2026-02-25,Basmati Rice 5kg,613
2026-02-26,Nike Air Max,7955
2026-02-26,Sony Headphones,5018
2026-02-26,Dabur Honey 1kg,453
2026-02-26,Basmati Rice 5kg,614
2026-02-27,Nike Air Max,7998
2026-02-27,Sony Headphones,4970
2026-02-27,Dabur Honey 1kg,453
2026-02-27,Basmati Rice 5kg,615
2026-02-28,Nike Air Max,8030
2026-02-28,Sony Headphones,5039
2026-02-28,Dabur Honey 1kg,450
2026-02-28,Basmati Rice 5kg,617
2026-03-01,Nike Air Max,8040
2026-03-01,Sony Headphones,4968
2026-03-01,Dabur Honey 1kg,445
2026-03-01,Basmati Rice 5kg,619
2026-03-02,Nike Air Max,8048
2026-03-02,Sony Headphones,4997
2026-03-02,Dabur Honey 1kg,446
2026-03-02,Basmati Rice 5kg,621
2026-03-03,Nike Air Max,7962
2026-03-03,Sony Headphones,5008
2026-03-03,Dabur Honey 1kg,449
2026-03-03,Basmati Rice 5kg,621
2026-03-04,Nike Air Max,7996
2026-03-04,Sony Headphones,4980
2026-03-04,Dabur Honey 1kg,450
2026-03-04,Basmati Rice 5kg,623
2026-03-05,Nike Air Max,8035
2026-03-05,Sony Headphones,4994
2026-03-05,Dabur Honey 1kg,455
2026-03-05,Basmati Rice 5kg,625
2026-03-06,Nike Air Max,8027
2026-03-06,Sony Headphones,4981
2026-03-06,Dabur Honey 1kg,453
2026-03-06,Basmati Rice 5kg,626
2026-03-07,Nike Air Max,7970
2026-03-07,Sony Headphones,5019
2026-03-07,Dabur Honey 1kg,451
2026-03-07,Basmati Rice 5kg,627
2026-03-08,Nike Air Max,8031
2026-03-08,Sony Headphones,5031
2026-03-08,Dabur Honey 1kg,448
2026-03-08,Basmati Rice 5kg,629
2026-03-09,Nike Air Max,8048
2026-03-09,Sony Headphones,4967
2026-03-09,Dabur Honey 1kg,448
2026-03-09,Basmati Rice 5kg,631
2026-03-10,Nike Air Max,7990
2026-03-10,Sony Headphones,5011
2026-03-10,Dabur Honey 1kg,449
2026-03-10,Basmati Rice 5kg,631
2026-03-11,Nike Air Max,8022
2026-03-11,Sony Headphones,5000
2026-03-11,Dabur Honey 1kg,448
2026-03-11,Basmati Rice 5kg,633
2026-03-12,Nike Air Max,8000
2026-03-12,Sony Headphones,5018
2026-03-12,Dabur Honey 1kg,447
2026-03-12,Basmati Rice 5kg,634
2026-03-13,Nike Air Max,7981
2026-03-13,Sony Headphones,5031
2026-03-13,Dabur Honey 1kg,453
2026-03-13,Basmati Rice 5kg,635
2026-03-14,Nike Air Max,8024
2026-03-14,Sony Headphones,5014
2026-03-14,Dabur Honey 1kg,454
2026-03-14,Basmati Rice 5kg,637
2026-03-15,Nike Air Max,7978
2026-03-15,Sony Headphones,4977
2026-03-15,Dabur Honey 1kg,453
2026-03-15,Basmati Rice 5kg,639
2026-03-16,Nike Air Max,8046
2026-03-16,Sony Headphones,4966
2026-03-16,Dabur Honey 1kg,446
2026-03-16,Basmati Rice 5kg,640
2026-03-17,Nike Air Max,7970
2026-03-17,Sony Headphones,5014
2026-03-17,Dabur Honey 1kg,454
2026-03-17,Basmati Rice 5kg,641
2026-03-18,Nike Air Max,7998
2026-03-18,Sony Headphones,5036
2026-03-18,Dabur Honey 1kg,452
2026-03-18,Basmati Rice 5kg,643
2026-03-19,Nike Air Max,8020
2026-03-19,Sony Headphones,4961
2026-03-19,Dabur Honey 1kg,455
2026-03-19,Basmati Rice 5kg,645
2026-03-20,Nike Air Max,8037
2026-03-20,Sony Headphones,5028
2026-03-20,Dabur Honey 1kg,449
2026-03-20,Basmati Rice 5kg,647
2026-03-21,Nike Air Max,7993
2026-03-21,Sony Headphones,4974
2026-03-21,Dabur Honey 1kg,449
2026-03-21,Basmati Rice 5kg,647
2026-03-22,Nike Air Max,8008
2026-03-22,Sony Headphones,4960
2026-03-22,Dabur Honey 1kg,449
2026-03-22,Basmati Rice 5kg,650
2026-03-23,Nike Air Max,8047
2026-03-23,Sony Headphones,4982
2026-03-23,Dabur Honey 1kg,453
2026-03-23,Basmati Rice 5kg,651
2026-03-24,Nike Air Max,8030
2026-03-24,Sony Headphones,4998
2026-03-24,Dabur Honey 1kg,455
2026-03-24,Basmati Rice 5kg,652
2026-03-25,Nike Air Max,7975
2026-03-25,Sony Headphones,4979
2026-03-25,Dabur Honey 1kg,450
2026-03-25,Basmati Rice 5kg,654
2026-03-26,Nike Air Max,8019
2026-03-26,Sony Headphones,5027
2026-03-26,Dabur Honey 1kg,445
2026-03-26,Basmati Rice 5kg,655
2026-03-27,Nike Air Max,8012
2026-03-27,Sony Headphones,4962
2026-03-27,Dabur Honey 1kg,446
2026-03-27,Basmati Rice 5kg,657
2026-03-28,Nike Air Max,7989
2026-03-28,Sony Headphones,4990
2026-03-28,Dabur Honey 1kg,445
2026-03-28,Basmati Rice 5kg,657
2026-03-29,Nike Air Max,8022
2026-03-29,Sony Headphones,4970
2026-03-29,Dabur Honey 1kg,446
2026-03-29,Basmati Rice 5kg,659
2026-03-30,Nike Air Max,7958
2026-03-30,Sony Headphones,5028
2026-03-30,Dabur Honey 1kg,447
2026-03-30,Basmati Rice 5kg,660
2026-03-31,Nike Air Max,8010
2026-03-31,Sony Headphones,5030
2026-03-31,Dabur Honey 1kg,447
2026-03-31,Basmati Rice 5kg,661
2026-04-01,Nike Air Max,8027
2026-04-01,Sony Headphones,5014
2026-04-01,Dabur Honey 1kg,448
2026-04-01,Basmati Rice 5kg,664
2026-04-02,Nike Air Max,8046
2026-04-02,Sony Headphones,4985
2026-04-02,Dabur Honey 1kg,449
2026-04-02,Basmati Rice 5kg,664
2026-04-03,Nike Air Max,8035
2026-04-03,Sony Headphones,5007
2026-04-03,Dabur Honey 1kg,452
2026-04-03,Basmati Rice 5kg,667
2026-04-04,Nike Air Max,8007
2026-04-04,Sony Headphones,4975
2026-04-04,Dabur Honey 1kg,448
2026-04-04,Basmati Rice 5kg,667
2026-04-05,Nike Air Max,7993
2026-04-05,Sony Headphones,4962
2026-04-05,Dabur Honey 1kg,454
2026-04-05,Basmati Rice 5kg,669
2026-04-06,Nike Air Max,8025
2026-04-06,Sony Headphones,4988
2026-04-06,Dabur Honey 1kg,445
2026-04-06,Basmati Rice 5kg,670
2026-04-07,Nike Air Max,8030
2026-04-07,Sony Headphones,4967
2026-04-07,Dabur Honey 1kg,448
2026-04-07,Basmati Rice 5kg,671
2026-04-08,Nike Air Max,7954
2026-04-08,Sony Headphones,5002
2026-04-08,Dabur Honey 1kg,446
2026-04-08,Basmati Rice 5kg,673
2026-04-09,Nike Air Max,7985
2026-04-09,Sony Headphones,5022
2026-04-09,Dabur Honey 1kg,448
2026-04-09,Basmati Rice 5kg,675
2026-04-10,Nike Air Max,8042
2026-04-10,Sony Headphones,5033
2026-04-10,Dabur Honey 1kg,454
2026-04-10,Basmati Rice 5kg,676
2026-04-11,Nike Air Max,8050
2026-04-11,Sony Headphones,5020
2026-04-11,Dabur Honey 1kg,451
2026-04-11,Basmati Rice 5kg,677
2026-04-12,Nike Air Max,7962
2026-04-12,Sony Headphones,5015
2026-04-12,Dabur Honey 1kg,450
2026-04-12,Basmati Rice 5kg,679
2026-04-13,Nike Air Max,8009
2026-04-13,Sony Headphones,4966
2026-04-13,Dabur Honey 1kg,455
2026-04-13,Basmati Rice 5kg,681
2026-04-14,Nike Air Max,8032
2026-04-14,Sony Headphones,4972
2026-04-14,Dabur Honey 1kg,445
2026-04-14,Basmati Rice 5kg,682
2026-04-15,Nike Air Max,7993
2026-04-15,Sony Headphones,4973
2026-04-15,Dabur Honey 1kg,448
2026-04-15,Basmati Rice 5kg,683
2026-04-16,Nike Air Max,8018
2026-04-16,Sony Headphones,5017
2026-04-16,Dabur Honey 1kg,447
2026-04-16,Basmati Rice 5kg,685
2026-04-17,Nike Air Max,7985
2026-04-17,Sony Headphones,5019
2026-04-17,Dabur Honey 1kg,448
2026-04-17,Basmati Rice 5kg,687
2026-04-18,Nike Air Max,7959
2026-04-18,Sony Headphones,5016
2026-04-18,Dabur Honey 1kg,453
2026-04-18,Basmati Rice 5kg,687
2026-04-19,Nike Air Max,8033
2026-04-19,Sony Headphones,5029
2026-04-19,Dabur Honey 1kg,445
2026-04-19,Basmati Rice 5kg,690
2026-04-20,Nike Air Max,8046
2026-04-20,Sony Headphones,4990
2026-04-20,Dabur Honey 1kg,447
2026-04-20,Basmati Rice 5kg,690
2026-04-21,Nike Air Max,8011
2026-04-21,Sony Headphones,4987
2026-04-21,Dabur Honey 1kg,451
2026-04-21,Basmati Rice 5kg,693
2026-04-22,Nike Air Max,7971
2026-04-22,Sony Headphones,5008
2026-04-22,Dabur Honey 1kg,445
2026-04-22,Basmati Rice 5kg,694
2026-04-23,Nike Air Max,7983
2026-04-23,Sony Headphones,5018
2026-04-23,Dabur Honey 1kg,449
2026-04-23,Basmati Rice 5kg,695
2026-04-24,Nike Air Max,8043
2026-04-24,Sony Headphones,5031
2026-04-24,Dabur Honey 1kg,455
2026-04-24,Basmati Rice 5kg,697
2026-04-25,Nike Air Max,7969
2026-04-25,Sony Headphones,4984
2026-04-25,Dabur Honey 1kg,449
2026-04-25,Basmati Rice 5kg,697
2026-04-26,Nike Air Max,7957
2026-04-26,Sony Headphones,5034
2026-04-26,Dabur Honey 1kg,453
2026-04-26,Basmati Rice 5kg,698
2026-04-27,Nike Air Max,7990
2026-04-27,Sony Headphones,4967
2026-04-27,Dabur Honey 1kg,445
2026-04-27,Basmati Rice 5kg,701
2026-04-28,Nike Air Max,8014
2026-04-28,Sony Headphones,5027
2026-04-28,Dabur Honey 1kg,447
2026-04-28,Basmati Rice 5kg,701
2026-04-29,Nike Air Max,8015
2026-04-29,Sony Headphones,4970
2026-04-29,Dabur Honey 1kg,447
2026-04-29,Basmati Rice 5kg,703
2026-04-30,Nike Air Max,7958
2026-04-30,Sony Headphones,4990
2026-04-30,Dabur Honey 1kg,451
2026-04-30,Basmati Rice 5kg,704
2026-05-01,Nike Air Max,8022
2026-05-01,Sony Headphones,4991
2026-05-01,Dabur Honey 1kg,454
2026-05-01,Basmati Rice 5kg,707
2026-05-02,Nike Air Max,8029
2026-05-02,Sony Headphones,4970
2026-05-02,Dabur Honey 1kg,451
2026-05-02,Basmati Rice 5kg,708
2026-05-03,Nike Air Max,8022
2026-05-03,Sony Headphones,5026
2026-05-03,Dabur Honey 1kg,450
2026-05-03,Basmati Rice 5kg,710
2026-05-04,Nike Air Max,7976
2026-05-04,Sony Headphones,5000
2026-05-04,Dabur Honey 1kg,448
2026-05-04,Basmati Rice 5kg,710
2026-05-05,Nike Air Max,7966
2026-05-05,Sony Headphones,4998
2026-05-05,Dabur Honey 1kg,452
2026-05-05,Basmati Rice 5kg,712
2026-05-06,Nike Air Max,8046
2026-05-06,Sony Headphones,4969
2026-05-06,Dabur Honey 1kg,445
2026-05-06,Basmati Rice 5kg,713
2026-05-07,Nike Air Max,8022
2026-05-07,Sony Headphones,4972
2026-05-07,Dabur Honey 1kg,446
2026-05-07,Basmati Rice 5kg,715
2026-05-08,Nike Air Max,8014
2026-05-08,Sony Headphones,4993
2026-05-08,Dabur Honey 1kg,447
2026-05-08,Basmati Rice 5kg,717
2026-05-09,Nike Air Max,7958
2026-05-09,Sony Headphones,4991
2026-05-09,Dabur Honey 1kg,450
2026-05-09,Basmati Rice 5kg,717
2026-05-10,Nike Air Max,8006
2026-05-10,Sony Headphones,5029
2026-05-10,Dabur Honey 1kg,449
2026-05-10,Basmati Rice 5kg,719
2026-05-11,Nike Air Max,8033
2026-05-11,Sony Headphones,5027
2026-05-11,Dabur Honey 1kg,445
2026-05-11,Basmati Rice 5kg,721
2026-05-12,Nike Air Max,8020
2026-05-12,Sony Headphones,4998
2026-05-12,Dabur Honey 1kg,455
2026-05-12,Basmati Rice 5kg,721
2026-05-13,Nike Air Max,7967
2026-05-13,Sony Headphones,4993
2026-05-13,Dabur Honey 1kg,446
2026-05-13,Basmati Rice 5kg,724
2026-05-14,Nike Air Max,8045
2026-05-14,Sony Headphones,5030
2026-05-14,Dabur Honey 1kg,447
2026-05-14,Basmati Rice 5kg,725
2026-05-15,Nike Air Max,8027
2026-05-15,Sony Headphones,4986
2026-05-15,Dabur Honey 1kg,450
2026-05-15,Basmati Rice 5kg,726
2026-05-16,Nike Air Max,8031
2026-05-16,Sony Headphones,4993
2026-05-16,Dabur Honey 1kg,453
2026-05-16,Basmati Rice 5kg,728
2026-05-17,Nike Air Max,7956
2026-05-17,Sony Headphones,4971
2026-05-17,Dabur Honey 1kg,455
2026-05-17,Basmati Rice 5kg,729
2026-05-18,Nike Air Max,7985
2026-05-18,Sony Headphones,4965
2026-05-18,Dabur Honey 1kg,445
2026-05-18,Basmati Rice 5kg,730
2026-05-19,Nike Air Max,7966
2026-05-19,Sony Headphones,4993
2026-05-19,Dabur Honey 1kg,447
2026-05-19,Basmati Rice 5kg,733
2026-05-20,Nike Air Max,8020
2026-05-20,Sony Headphones,5014
2026-05-20,Dabur Honey 1kg,453
2026-05-20,Basmati Rice 5kg,733
2026-05-21,Nike Air Max,7959
2026-05-21,Sony Headphones,4979
2026-05-21,Dabur Honey 1kg,453
2026-05-21,Basmati Rice 5kg,734
2026-05-22,Nike Air Max,7997
2026-05-22,Sony Headphones,5034
2026-05-22,Dabur Honey 1kg,453
2026-05-22,Basmati Rice 5kg,736
2026-05-23,Nike Air Max,7966
2026-05-23,Sony Headphones,4965
2026-05-23,Dabur Honey 1kg,449
2026-05-23,Basmati Rice 5kg,738
2026-05-24,Nike Air Max,7955
2026-05-24,Sony Headphones,5005
2026-05-24,Dabur Honey 1kg,448
2026-05-24,Basmati Rice 5kg,740
2026-05-25,Nike Air Max,8035
2026-05-25,Sony Headphones,4973
2026-05-25,Dabur Honey 1kg,450
2026-05-25,Basmati Rice 5kg,741
2026-05-26,Nike Air Max,8002
2026-05-26,Sony Headphones,5039
2026-05-26,Dabur Honey 1kg,447
2026-05-26,Basmati Rice 5kg,743
2026-05-27,Nike Air Max,7980
2026-05-27,Sony Headphones,4980
2026-05-27,Dabur Honey 1kg,447
2026-05-27,Basmati Rice 5kg,744
2026-05-28,Nike Air Max,7953
2026-05-28,Sony Headphones,4982
2026-05-28,Dabur Honey 1kg,450
2026-05-28,Basmati Rice 5kg,746
2026-05-29,Nike Air Max,8002
2026-05-29,Sony Headphones,4991
2026-05-29,Dabur Honey 1kg,449
2026-05-29,Basmati Rice 5kg,746
2026-05-30,Nike Air Max,8039
2026-05-30,Sony Headphones,4973
2026-05-30,Dabur Honey 1kg,451
2026-05-30,Basmati Rice 5kg,749
2026-05-31,Nike Air Max,8010
2026-05-31,Sony Headphones,4988
2026-05-31,Dabur Honey 1kg,448
2026-05-31,Basmati Rice 5kg,750
2026-06-01,Nike Air Max,8008
2026-06-01,Sony Headphones,5004
2026-06-01,Dabur Honey 1kg,449
2026-06-01,Basmati Rice 5kg,752
2026-06-02,Nike Air Max,7979
2026-06-02,Sony Headphones,4988
2026-06-02,Dabur Honey 1kg,445
2026-06-02,Basmati Rice 5kg,753
2026-06-03,Nike Air Max,8001
2026-06-03,Sony Headphones,5002
2026-06-03,Dabur Honey 1kg,449
2026-06-03,Basmati Rice 5kg,754
2026-06-04,Nike Air Max,8048
2026-06-04,Sony Headphones,4995
2026-06-04,Dabur Honey 1kg,450
2026-06-04,Basmati Rice 5kg,755
2026-06-05,Nike Air Max,8001
2026-06-05,Sony Headphones,5028
2026-06-05,Dabur Honey 1kg,450
2026-06-05,Basmati Rice 5kg,757
2026-06-06,Nike Air Max,7964
2026-06-06,Sony Headphones,4993
2026-06-06,Dabur Honey 1kg,447
2026-06-06,Basmati Rice 5kg,758
2026-06-07,Nike Air Max,7983
2026-06-07,Sony Headphones,4964
2026-06-07,Dabur Honey 1kg,446
2026-06-07,Basmati Rice 5kg,760
2026-06-08,Nike Air Max,7994
2026-06-08,Sony Headphones,5000
2026-06-08,Dabur Honey 1kg,451
2026-06-08,Basmati Rice 5kg,761
2026-06-09,Nike Air Max,8015
2026-06-09,Sony Headphones,4974
2026-06-09,Dabur Honey 1kg,451
2026-06-09,Basmati Rice 5kg,763
2026-06-10,Nike Air Max,7974
2026-06-10,Sony Headphones,4992
2026-06-10,Dabur Honey 1kg,445
2026-06-10,Basmati Rice 5kg,764
2026-06-11,Nike Air Max,7950
2026-06-11,Sony Headphones,5026
2026-06-11,Dabur Honey 1kg,453
2026-06-11,Basmati Rice 5kg,766
2026-06-12,Nike Air Max,8044
2026-06-12,Sony Headphones,4985
2026-06-12,Dabur Honey 1kg,450
2026-06-12,Basmati Rice 5kg,767
2026-06-13,Nike Air Max,8035
2026-06-13,Sony Headphones,5002
2026-06-13,Dabur Honey 1kg,454
2026-06-13,Basmati Rice 5kg,768
2026-06-14,Nike Air Max,7965
2026-06-14,Sony Headphones,4998
2026-06-14,Dabur Honey 1kg,453
2026-06-14,Basmati Rice 5kg,769
2026-06-15,Nike Air Max,8002
2026-06-15,Sony Headphones,5001
2026-06-15,Dabur Honey 1kg,451
2026-06-15,Basmati Rice 5kg,771
2026-06-16,Nike Air Max,8020
2026-06-16,Sony Headphones,4976
2026-06-16,Dabur Honey 1kg,448
2026-06-16,Basmati Rice 5kg,772
2026-06-17,Nike Air Max,7998
2026-06-17,Sony Headphones,4982
2026-06-17,Dabur Honey 1kg,454
2026-06-17,Basmati Rice 5kg,774
2026-06-18,Nike Air Max,8001
2026-06-18,Sony Headphones,5030
2026-06-18,Dabur Honey 1kg,445
2026-06-18,Basmati Rice 5kg,775
2026-06-19,Nike Air Max,7976
2026-06-19,Sony Headphones,5015
2026-06-19,Dabur Honey 1kg,454
2026-06-19,Basmati Rice 5kg,777
2026-06-20,Nike Air Max,7991
2026-06-20,Sony Headphones,5019
2026-06-20,Dabur Honey 1kg,452
2026-06-20,Basmati Rice 5kg,778
2026-06-21,Nike Air Max,7977
2026-06-21,Sony Headphones,5025
2026-06-21,Dabur Honey 1kg,452
2026-06-21,Basmati Rice 5kg,780
2026-06-22,Nike Air Max,8044
2026-06-22,Sony Headphones,4981
2026-06-22,Dabur Honey 1kg,455
2026-06-22,Basmati Rice 5kg,780
2026-06-23,Nike Air Max,8015
2026-06-23,Sony Headphones,5039
2026-06-23,Dabur Honey 1kg,450
2026-06-23,Basmati Rice 5kg,782
2026-06-24,Nike Air Max,8046
2026-06-24,Sony Headphones,4990
2026-06-24,Dabur Honey 1kg,455
2026-06-24,Basmati Rice 5kg,784
2026-06-25,Nike Air Max,7975
2026-06-25,Sony Headphones,4978
2026-06-25,Dabur Honey 1kg,445
2026-06-25,Basmati Rice 5kg,784
2026-06-26,Nike Air Max,8010
2026-06-26,Sony Headphones,5038
2026-06-26,Dabur Honey 1kg,446
2026-06-26,Basmati Rice 5kg,787
2026-06-27,Nike Air Max,8030
2026-06-27,Sony Headphones,5033
2026-06-27,Dabur Honey 1kg,448
2026-06-27,Basmati Rice 5kg,789
2026-06-28,Nike Air Max,7999
2026-06-28,Sony Headphones,5023
2026-06-28,Dabur Honey 1kg,451
2026-06-28,Basmati Rice 5kg,789
2026-06-29,Nike Air Max,8033
2026-06-29,Sony Headphones,4960
2026-06-29,Dabur Honey 1kg,446
2026-06-29,Basmati Rice 5kg,792
2026-06-30,Nike Air Max,7978
2026-06-30,Sony Headphones,4982
2026-06-30,Dabur Honey 1kg,453
2026-06-30,Basmati Rice 5kg,792
2026-07-01,Nike Air Max,8021
2026-07-01,Sony Headphones,4991
2026-07-01,Dabur Honey 1kg,446
2026-07-01,Basmati Rice 5kg,794
2026-07-02,Nike Air Max,8009
2026-07-02,Sony Headphones,5027
2026-07-02,Dabur Honey 1kg,453
2026-07-02,Basmati Rice 5kg,796
2026-07-03,Nike Air Max,8046
2026-07-03,Sony Headphones,5016
2026-07-03,Dabur Honey 1kg,454
2026-07-03,Basmati Rice 5kg,797
2026-07-04,Nike Air Max,8014
2026-07-04,Sony Headphones,5014
2026-07-04,Dabur Honey 1kg,453
2026-07-04,Basmati Rice 5kg,798
2026-07-05,Nike Air Max,7970
2026-07-05,Sony Headphones,5020
2026-07-05,Dabur Honey 1kg,452
2026-07-05,Basmati Rice 5kg,799
2026-07-06,Nike Air Max,7981
2026-07-06,Sony Headphones,4995
2026-07-06,Dabur Honey 1kg,453
2026-07-06,Basmati Rice 5kg,801
2026-07-07,Nike Air Max,7980
2026-07-07,Sony Headphones,4995
2026-07-07,Dabur Honey 1kg,452
2026-07-07,Basmati Rice 5kg,802
2026-07-08,Nike Air Max,7986
2026-07-08,Sony Headphones,4990
2026-07-08,Dabur Honey 1kg,449
2026-07-08,Basmati Rice 5kg,804
2026-07-09,Nike Air Max,8019
2026-07-09,Sony Headphones,4970
2026-07-09,Dabur Honey 1kg,447
2026-07-09,Basmati Rice 5kg,805
2026-07-10,Nike Air Max,7999
2026-07-10,Sony Headphones,4979
2026-07-10,Dabur Honey 1kg,448
2026-07-10,Basmati Rice 5kg,806
2026-07-11,Nike Air Max,8002
2026-07-11,Sony Headphones,5002
2026-07-11,Dabur Honey 1kg,453
2026-07-11,Basmati Rice 5kg,808
2026-07-12,Nike Air Max,7957
2026-07-12,Sony Headphones,4986
2026-07-12,Dabur Honey 1kg,451
2026-07-12,Basmati Rice 5kg,810
2026-07-13,Nike Air Max,8048
2026-07-13,Sony Headphones,5034
2026-07-13,Dabur Honey 1kg,445
2026-07-13,Basmati Rice 5kg,812
2026-07-14,Nike Air Max,8047
2026-07-14,Sony Headphones,5033
2026-07-14,Dabur Honey 1kg,451
2026-07-14,Basmati Rice 5kg,813
2026-07-15,Nike Air Max,7995
2026-07-15,Sony Headphones,4998
2026-07-15,Dabur Honey 1kg,451
2026-07-15,Basmati Rice 5kg,815
2026-07-16,Nike Air Max,8003
2026-07-16,Sony Headphones,5028
2026-07-16,Dabur Honey 1kg,453
2026-07-16,Basmati Rice 5kg,816
2026-07-17,Nike Air Max,7978
2026-07-17,Sony Headphones,5022
2026-07-17,Dabur Honey 1kg,448
2026-07-17,Basmati Rice 5kg,816
2026-07-18,Nike Air Max,8012
2026-07-18,Sony Headphones,4963
2026-07-18,Dabur Honey 1kg,451
2026-07-18,Basmati Rice 5kg,818
2026-07-19,Nike Air Max,8036
2026-07-19,Sony Headphones,5011
2026-07-19,Dabur Honey 1kg,447
2026-07-19,Basmati Rice 5kg,821
2026-07-20,Nike Air Max,7966
2026-07-20,Sony Headphones,5039
2026-07-20,Dabur Honey 1kg,453
2026-07-20,Basmati Rice 5kg,820
2026-07-21,Nike Air Max,8000
2026-07-21,Sony Headphones,5035
2026-07-21,Dabur Honey 1kg,454
2026-07-21,Basmati Rice 5kg,823
2026-07-22,Nike Air Max,7960
2026-07-22,Sony Headphones,5014
2026-07-22,Dabur Honey 1kg,447
2026-07-22,Basmati Rice 5kg,825
2026-07-23,Nike Air Max,7973
2026-07-23,Sony Headphones,4966
2026-07-23,Dabur Honey 1kg,449
2026-07-23,Basmati Rice 5kg,825
2026-07-24,Nike Air Max,7977
2026-07-24,Sony Headphones,5018
2026-07-24,Dabur Honey 1kg,450
2026-07-24,Basmati Rice 5kg,827
2026-07-25,Nike Air Max,7998
2026-07-25,Sony Headphones,4995
2026-07-25,Dabur Honey 1kg,451
2026-07-25,Basmati Rice 5kg,828
2026-07-26,Nike Air Max,7960
2026-07-26,Sony Headphones,5020
2026-07-26,Dabur Honey 1kg,445
2026-07-26,Basmati Rice 5kg,830
2026-07-27,Nike Air Max,7956
2026-07-27,Sony Headphones,5004
2026-07-27,Dabur Honey 1kg,448
2026-07-27,Basmati Rice 5kg,832
2026-07-28,Nike Air Max,8049
2026-07-28,Sony Headphones,4965
2026-07-28,Dabur Honey 1kg,445
2026-07-28,Basmati Rice 5kg,834
2026-07-29,Nike Air Max,7975
2026-07-29,Sony Headphones,4962
2026-07-29,Dabur Honey 1kg,454
2026-07-29,Basmati Rice 5kg,834
2026-07-30,Nike Air Max,7966
2026-07-30,Sony Headphones,5020
2026-07-30,Dabur Honey 1kg,455
2026-07-30,Basmati Rice 5kg,835
2026-07-31,Nike Air Max,7977
2026-07-31,Sony Headphones,8999
2026-07-31,Dabur Honey 1kg,452
2026-07-31,Basmati Rice 5kg,837
2026-08-01,Nike Air Max,8048
2026-08-01,Sony Headphones,8999
2026-08-01,Dabur Honey 1kg,450
2026-08-01,Basmati Rice 5kg,838
2026-08-02,Nike Air Max,8027
2026-08-02,Sony Headphones,8999
2026-08-02,Dabur Honey 1kg,446
2026-08-02,Basmati Rice 5kg,840
2026-08-03,Nike Air Max,7970
2026-08-03,Sony Headphones,8999
2026-08-03,Dabur Honey 1kg,449
2026-08-03,Basmati Rice 5kg,841
2026-08-04,Nike Air Max,7953
2026-08-04,Sony Headphones,8999
2026-08-04,Dabur Honey 1kg,449
2026-08-04,Basmati Rice 5kg,843
2026-08-05,Nike Air Max,7998
2026-08-05,Sony Headphones,8999
2026-08-05,Dabur Honey 1kg,451
2026-08-05,Basmati Rice 5kg,845
2026-08-06,Nike Air Max,7975
2026-08-06,Sony Headphones,8999
2026-08-06,Dabur Honey 1kg,446
2026-08-06,Basmati Rice 5kg,846
2026-08-07,Nike Air Max,8030
2026-08-07,Sony Headphones,8999
2026-08-07,Dabur Honey 1kg,448
2026-08-07,Basmati Rice 5kg,846
2026-08-08,Nike Air Max,8048
2026-08-08,Sony Headphones,8999
2026-08-08,Dabur Honey 1kg,449
2026-08-08,Basmati Rice 5kg,849
2026-08-09,Nike Air Max,8026
2026-08-09,Sony Headphones,8999
2026-08-09,Dabur Honey 1kg,446
2026-08-09,Basmati Rice 5kg,851
2026-08-10,Nike Air Max,4999
2026-08-10,Sony Headphones,4899
2026-08-10,Dabur Honey 1kg,440
2026-08-10,Basmati Rice 5kg,810
2026-08-11,Nike Air Max,4999
2026-08-11,Sony Headphones,4899
2026-08-11,Dabur Honey 1kg,440
2026-08-11,Basmati Rice 5kg,810
2026-08-12,Nike Air Max,4999
2026-08-12,Sony Headphones,4899
2026-08-12,Dabur Honey 1kg,440
2026-08-12,Basmati Rice 5kg,810
2026-08-13,Nike Air Max,4999
2026-08-13,Sony Headphones,4899
2026-08-13,Dabur Honey 1kg,440
2026-08-13,Basmati Rice 5kg,810
2026-08-14,Nike Air Max,4999
2026-08-14,Sony Headphones,4899
2026-08-14,Dabur Honey 1kg,440
2026-08-14,Basmati Rice 5kg,810
"""

df = pd.read_csv(io.StringIO(csv_data))
df['date'] = pd.to_datetime(df['date'])
sale_date_str = '2026-08-10'
sale_ts = pd.Timestamp(sale_date_str)

for product in df['product_name'].unique():
    product_df = df[df['product_name'] == product].sort_values('date')
    
    # get the price on 2026-08-09 as original, and 2026-08-10 as sale
    pre_sale_df = product_df[product_df['date'] < sale_ts]
    sale_price = float(product_df[product_df['date'] == sale_ts]['price'].iloc[0])
    
    # for original price, take max of last 10 days before sale to capture the dark pattern correctly
    last_10 = pre_sale_df.tail(10)
    original_price = float(last_10['price'].max())

    features = extract_features(product_df, original_price, sale_price, sale_date_str, product)
    result = analyze(features)
    explanation = generate_explanation(features, result)

    print(f"================ {product} ================")
    print(explanation)
    print("\n")
