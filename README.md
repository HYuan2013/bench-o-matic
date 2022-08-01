# bench-o-matic
Automate running browserbench.org benchmarks

Params:
* `-r,--runs`: Number of runs. i.e. `python3 bom.py --runs 100`

## MacOS
Requires Python 3 native to the system CPU architecture (MacOS 12.3.1+ recommended).

```bash
python3 -m pip install --upgrade pip
python3 -m pip install selenium psutil webdriver-manager requests
```

Also need to enable safaridriver support (once)
```
sudo safaridriver --enable
```

## Windows
Example usage: C:\Users\windo\Documents\GitHub\bench-o-matic>python bom.py --runs 20 --full_speedometer2_score=True --sleep_interval=0 > log_test.txt