#include <vector>
#include <string>
#include <iostream>
#include <cstring>
#include <algorithm>

const std::string IN_PATH = "/media/work/Waveforms/run4/100-200.root";
const std::string OUT_PATH = "/media/work/Waveforms/run4/analysis/amplitudes/new/100-200.root";

// The first channel to consider...
const int FIRST_CHANNEL = 0;
// ...and the last one (included)
const int LAST_CHANNEL = 10;

// How many samples to take before...
const int BEFORE_PEAK = 3;
// ...and after peak to do a gaussian fit
const int AFTER_PEAK = 3;

// How many samples to use to calculate baseline, starting from the end
const int NUM_AVERAGE = 100;
// Reciprocal of frequency
const double TIME_STEP = 2E-10;

// Don't touch!
const int NUM_CHANNELS = LAST_CHANNEL - FIRST_CHANNEL;
const int NUM_SAMPLES = BEFORE_PEAK + AFTER_PEAK + 1;

void analyze(TTree *in, TTree *out) {
    // Output tree setup
    std::vector<double> position(2, 0);
    std::vector<double>* ptr = &position;
    out->Branch("pos", ptr);

    std::vector<double> amplitudes(NUM_CHANNELS, 0);
    for(int i = FIRST_CHANNEL; i <= LAST_CHANNEL; i++) {
        std::string amp = "amp" + std::to_string(i);
        out->Branch(amp.c_str(), &(amplitudes[i - FIRST_CHANNEL]));
    }

    // Input tree setup
    in->SetBranchAddress("pos", &ptr);

    std::vector<std::vector<double>*> channels(NUM_CHANNELS, 0);
    for(int i = FIRST_CHANNEL; i <= LAST_CHANNEL; i++) {
        std::string chn = "w" + std::to_string(i);
        in->SetBranchAddress(chn.c_str(), &(channels[i - FIRST_CHANNEL]));
    }

    std::vector<double> time;
    for(int i = 0; i < NUM_SAMPLES; i++) {
        time.push_back(i * TIME_STEP);
    }

    TF1 *fit = new TF1("fit", "gaus");

    int events = in->GetEntries();
    // Branches interation
    for(int i = 0; i < events; i++) {
        in->GetEntry(i);

        for(int j = FIRST_CHANNEL; j <= LAST_CHANNEL; j++) {
            std::vector<double>* channel = channels[j - FIRST_CHANNEL];

            double average = std::accumulate(channel->end() - NUM_AVERAGE,
                channel->end(), 0) / NUM_AVERAGE;

            int peak = std::max_element(channel->begin(),
                channel->end()) - channel->begin();
            auto begin = channel->begin() + peak - BEFORE_PEAK;
            auto end = channel->begin() + peak + AFTER_PEAK + 1;
            std::vector<double> event(begin, end);

            TGraph *graph = new TGraph(NUM_SAMPLES, &time[0], &event[0]);
            graph->Fit(fit, "MNQ");
            amplitudes[j - FIRST_CHANNEL] = fit->GetParameter(0) - average;
        }

        out->Fill();
        if(i % 100 == 0) {
            std::cout << "Progress: " << i << "/" << events << std::endl;
            out->Write();
        }
    }
    out->Write();
    in->ResetBranchAddresses();
}

void preprocessing() {
    TFile *in = TFile::Open(IN_PATH.c_str(), "READ");
    TTree *tree = (TTree*) in->Get("wfm");

    TFile *out = TFile::Open(OUT_PATH.c_str(), "CREATE");
    TTree *data = new TTree("data", "Analysis data");

    analyze(tree, data);

    out->Close();
    in->Close();
}
