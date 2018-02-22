make clean
make
rm -rf build
python setup_gpu.py build
sudo python setup_gpu.py install
