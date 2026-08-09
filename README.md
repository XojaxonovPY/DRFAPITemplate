Munosabat turi,Qaysi taraf so'ralmoqda?,Ishlatilishi kerak,SQL Mexanizmi
ForeignKey (1-to-N),Child -> Parent (Product -> Category),"select_related(""category"")",JOIN (1 ta query)
Reverse ForeignKey,Parent -> Children (Category -> Products),"prefetch_related(""products"")",IN (...) (2 ta query)
Many-to-Many (N-to-N),Har qanday taraf (Product <-> Tag),"prefetch_related(""tags"")",IN (...) (2 yoki 3 ta query)
One-to-One (1-to-1),Har qanday taraf,"select_related(""profile"")",JOIN (1 ta query)
